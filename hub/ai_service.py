# ai_service.py - Forest Guardian Hub
# Azure AI Services Integration for Spectrogram Analysis
# Supports BOTH Azure Custom Vision AND GPT-4o Vision

import os
import base64
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from config import Config

logger = logging.getLogger(__name__)

# =============================================================================
# AI MODE CONFIGURATION
# =============================================================================
# Can be set via dashboard: 'gpt4o', 'custom_vision', or 'auto'
# 'auto' uses Custom Vision for fast classification, GPT-4o for verification
current_ai_mode = 'gpt4o'  # Default mode

def get_ai_mode():
    """Get current AI analysis mode"""
    return current_ai_mode

def set_ai_mode(mode: str):
    """Set AI analysis mode: 'gpt4o', 'custom_vision', or 'auto'"""
    global current_ai_mode
    if mode in ['gpt4o', 'custom_vision', 'auto']:
        current_ai_mode = mode
        logger.info(f"AI mode set to: {mode}")
        return True
    return False


# =============================================================================
# AZURE OPENAI CLIENT (GPT-4o Vision)
# =============================================================================
openai_client = None

def init_azure_openai():
    """Initialize Azure OpenAI client"""
    global openai_client
    if openai_client is None and Config.AZURE_OPENAI_KEY and Config.AZURE_OPENAI_ENDPOINT:
        try:
            from openai import AzureOpenAI
            openai_client = AzureOpenAI(
                api_key=Config.AZURE_OPENAI_KEY,
                api_version="2024-02-15-preview",
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
            )
            logger.info("Azure OpenAI client initialized")
        except Exception as e:
            logger.error(f"Failed to init Azure OpenAI: {e}")
    return openai_client


# =============================================================================
# AZURE CUSTOM VISION CLIENT
# =============================================================================
def analyze_with_custom_vision(image_path: str) -> Dict[str, Any]:
    """
    Analyze spectrogram using Azure Custom Vision
    
    Requires:
    - AZURE_CUSTOM_VISION_ENDPOINT
    - AZURE_CUSTOM_VISION_KEY
    - AZURE_CUSTOM_VISION_PROJECT_ID
    - AZURE_CUSTOM_VISION_ITERATION
    """
    result = {
        "success": False,
        "classification": "unknown",
        "confidence": 0,
        "threat_level": "NONE",
        "service": "custom_vision",
        "all_predictions": []
    }
    
    if not all([Config.AZURE_CUSTOM_VISION_ENDPOINT, Config.AZURE_CUSTOM_VISION_KEY]):
        result["error"] = "Azure Custom Vision not configured"
        logger.warning(result["error"])
        return result
    
    try:
        # Read image
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
        
        # Build prediction URL
        # Format: https://{endpoint}/customvision/v3.0/Prediction/{project_id}/classify/iterations/{iteration}/image
        url = f"{Config.AZURE_CUSTOM_VISION_ENDPOINT}/customvision/v3.0/Prediction/{Config.AZURE_CUSTOM_VISION_PROJECT_ID}/classify/iterations/{Config.AZURE_CUSTOM_VISION_ITERATION}/image"
        
        headers = {
            "Prediction-Key": Config.AZURE_CUSTOM_VISION_KEY,
            "Content-Type": "application/octet-stream"
        }
        
        response = requests.post(url, headers=headers, data=image_data, timeout=10)
        response.raise_for_status()
        
        predictions = response.json().get("predictions", [])
        
        if predictions:
            # Get top prediction
            top = max(predictions, key=lambda x: x.get("probability", 0))
            result["success"] = True
            result["classification"] = top.get("tagName", "unknown").lower()
            result["confidence"] = int(top.get("probability", 0) * 100)
            result["all_predictions"] = [
                {"tag": p["tagName"], "confidence": int(p["probability"] * 100)}
                for p in sorted(predictions, key=lambda x: -x.get("probability", 0))
            ]
            
            # Map classification to threat level
            if result["classification"] == "chainsaw":
                result["threat_level"] = "CRITICAL" if result["confidence"] > 80 else "HIGH"
            elif result["classification"] == "vehicle":
                result["threat_level"] = "MEDIUM"
            else:
                result["threat_level"] = "LOW" if result["confidence"] > 70 else "NONE"
            
            logger.info(f"Custom Vision: {result['classification']} ({result['confidence']}%)")
        
    except requests.exceptions.RequestException as e:
        result["error"] = f"Custom Vision API error: {str(e)}"
        logger.error(result["error"])
    except Exception as e:
        result["error"] = f"Custom Vision error: {str(e)}"
        logger.error(result["error"])
    
    return result


# =============================================================================
# GPT-4o VISION PROMPTS
# =============================================================================

SPECTROGRAM_SYSTEM_PROMPT = """You are an expert audio spectrogram analyst for a forest protection system. 
Your job is to analyze mel-frequency spectrograms (64x64 grayscale images) to detect illegal logging activity.

SPECTROGRAM INTERPRETATION:
- X-axis: Time (left to right, ~4 seconds total)
- Y-axis: Mel frequency bins (low frequencies at bottom, high at top)
- Brightness: Energy intensity (brighter = louder)

CHAINSAW CHARACTERISTICS (HIGH THREAT):
- Strong horizontal bands between 200-4000 Hz (middle portion of spectrogram)
- Distinctive periodic pattern from engine RPM (saw-tooth or striped appearance)
- Modulation patterns when cutting (wavering intensity in mid-frequencies)
- Duration: sustained pattern lasting several seconds

VEHICLE SOUNDS (MEDIUM THREAT):
- Low frequency rumble (bottom of spectrogram)
- Less periodic than chainsaw
- May indicate loggers arriving/leaving

NATURAL FOREST SOUNDS (NO THREAT):
- Bird calls: short vertical bursts at various frequencies
- Wind: diffuse low-frequency noise
- Rain: broadband noise across all frequencies
- Thunder: sudden broadband impulse
- Animal calls: isolated patterns, not sustained

CONFIDENCE SCORING (be precise and varied):
- 95-100%: Perfect textbook example, extremely clear features
- 85-94%: Very clear features, high certainty
- 70-84%: Probable match, some features present but not all
- 50-69%: Possible match, features are ambiguous
- Below 50%: Unlikely match, use a different classification

Be critical and use the FULL confidence range. Not every chainsaw spectrogram is 95%.

RESPOND IN THIS EXACT JSON FORMAT:
{
    "classification": "chainsaw" | "vehicle" | "natural" | "unknown",
    "confidence": 0-100,
    "threat_level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "NONE",
    "reasoning": "Brief explanation of visual features detected",
    "features_detected": ["list", "of", "key", "features"],
    "recommended_action": "What should rangers do"
}"""

def analyze_spectrogram(image_path: str, node_id: str = "", location: Tuple[float, float] = (0, 0)) -> Dict[str, Any]:
    """
    Analyze a spectrogram image using selected AI service
    
    Mode controlled by current_ai_mode:
    - 'gpt4o': Use Azure GPT-4o Vision
    - 'custom_vision': Use Azure Custom Vision
    - 'auto': Use Custom Vision first, GPT-4o for verification if threat detected
    
    Args:
        image_path: Path to the spectrogram PNG/PGM file
        node_id: ID of the sensor node that captured the audio
        location: (latitude, longitude) tuple
        
    Returns:
        Dictionary with classification results
    """
    global current_ai_mode
    
    result = {
        "success": False,
        "classification": "unknown",
        "confidence": 0,
        "threat_level": "NONE",
        "reasoning": "",
        "features_detected": [],
        "recommended_action": "",
        "analysis_time": datetime.utcnow().isoformat(),
        "node_id": node_id,
        "location": {"lat": location[0], "lon": location[1]},
        "image_path": image_path,
        "ai_mode": current_ai_mode,
        "service_used": ""
    }
    
    if not os.path.exists(image_path):
        result["error"] = f"Spectrogram file not found: {image_path}"
        logger.error(result["error"])
        return result
    
    # Route to appropriate AI service based on mode
    if current_ai_mode == 'custom_vision':
        return _analyze_with_custom_vision_full(image_path, node_id, location, result)
    elif current_ai_mode == 'gpt4o':
        return _analyze_with_gpt4o_vision(image_path, node_id, location, result)
    elif current_ai_mode == 'auto':
        # Auto mode: Custom Vision for speed, GPT-4o for verification
        cv_result = analyze_with_custom_vision(image_path)
        if cv_result["success"]:
            result.update(cv_result)
            result["service_used"] = "custom_vision"
            
            # If threat detected, verify with GPT-4o
            if cv_result["threat_level"] in ["CRITICAL", "HIGH", "MEDIUM"]:
                logger.info("Threat detected by Custom Vision, verifying with GPT-4o...")
                gpt_result = _analyze_with_gpt4o_vision(image_path, node_id, location, result.copy())
                if gpt_result["success"]:
                    result["gpt4o_verification"] = {
                        "classification": gpt_result["classification"],
                        "confidence": gpt_result["confidence"],
                        "threat_level": gpt_result["threat_level"],
                        "reasoning": gpt_result.get("reasoning", "")
                    }
                    result["service_used"] = "custom_vision+gpt4o"
                    
                    # Use GPT-4o's more detailed analysis
                    if gpt_result.get("reasoning"):
                        result["reasoning"] = gpt_result["reasoning"]
                    if gpt_result.get("features_detected"):
                        result["features_detected"] = gpt_result["features_detected"]
                    if gpt_result.get("recommended_action"):
                        result["recommended_action"] = gpt_result["recommended_action"]
        else:
            # Custom Vision failed, fall back to GPT-4o
            logger.warning("Custom Vision failed, falling back to GPT-4o")
            return _analyze_with_gpt4o_vision(image_path, node_id, location, result)
        
        return result
    else:
        result["error"] = f"Unknown AI mode: {current_ai_mode}"
        return result


def _analyze_with_custom_vision_full(image_path: str, node_id: str, location: Tuple[float, float], result: Dict) -> Dict[str, Any]:
    """Full Custom Vision analysis with all fields populated"""
    cv_result = analyze_with_custom_vision(image_path)
    result.update(cv_result)
    result["service_used"] = "custom_vision"
    result["node_id"] = node_id
    result["location"] = {"lat": location[0], "lon": location[1]}
    
    # Add recommended actions based on classification
    if result["classification"] == "chainsaw":
        result["recommended_action"] = "URGENT: Dispatch rangers immediately. Potential illegal logging in progress."
        result["features_detected"] = ["periodic engine pattern", "mid-frequency bands"]
    elif result["classification"] == "vehicle":
        result["recommended_action"] = "Monitor area. Vehicle detected - could indicate loggers."
        result["features_detected"] = ["low-frequency rumble"]
    else:
        result["recommended_action"] = "No action needed. Natural forest sounds."
        result["features_detected"] = ["natural ambient sounds"]
    
    return result


def _analyze_with_gpt4o_vision(image_path: str, node_id: str, location: Tuple[float, float], result: Dict) -> Dict[str, Any]:
    """
    Analyze spectrogram using Azure GPT-4o Vision
    """
    init_azure_openai()
    
    if openai_client is None:
        result["error"] = "Azure OpenAI client not initialized"
        logger.error(result["error"])
        return result
    
    result["service_used"] = "gpt4o"
    
    try:
        # Read and encode the image
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Determine image type
        if image_path.lower().endswith('.png'):
            media_type = "image/png"
        elif image_path.lower().endswith('.pgm'):
            media_type = "image/x-portable-graymap"
        else:
            media_type = "image/png"  # Default
        
        # Create user message with context
        user_message = f"""Analyze this audio spectrogram captured by forest monitoring sensor.

Context:
- Node ID: {node_id}
- Location: {location[0]:.6f}, {location[1]:.6f}
- Capture Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
- Spectrogram: 64x64 mel-frequency bins, ~4 second audio window

Please classify this spectrogram and assess threat level."""

        # Call Azure GPT-4o Vision
        response = openai_client.chat.completions.create(
            model=Config.AZURE_OPENAI_DEPLOYMENT,  # Should be "gpt-4o" or your deployment name
            messages=[
                {"role": "system", "content": SPECTROGRAM_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_data}",
                                "detail": "high"  # Use high detail for spectrogram analysis
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.1  # Low temperature for consistent classification
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        logger.info(f"GPT-4o Vision response: {response_text}")
        
        # Try to parse as JSON
        import json
        try:
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            parsed = json.loads(json_str)
            result.update({
                "success": True,
                "classification": parsed.get("classification", "unknown"),
                "confidence": parsed.get("confidence", 0),
                "threat_level": parsed.get("threat_level", "NONE"),
                "reasoning": parsed.get("reasoning", ""),
                "features_detected": parsed.get("features_detected", []),
                "recommended_action": parsed.get("recommended_action", "")
            })
        except json.JSONDecodeError:
            # If JSON parsing fails, extract key info from text
            result["success"] = True
            result["reasoning"] = response_text
            
            # Simple keyword detection
            response_lower = response_text.lower()
            if "chainsaw" in response_lower:
                result["classification"] = "chainsaw"
                result["threat_level"] = "CRITICAL"
                result["confidence"] = 75
            elif "vehicle" in response_lower or "truck" in response_lower:
                result["classification"] = "vehicle"
                result["threat_level"] = "MEDIUM"
                result["confidence"] = 60
            else:
                result["classification"] = "natural"
                result["threat_level"] = "LOW"
                result["confidence"] = 50
        
        logger.info(f"Spectrogram analysis complete: {result['classification']} ({result['confidence']}%)")
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Spectrogram analysis failed: {e}")
    
    return result


def analyze_spectrogram_batch(image_paths: list, node_data: list = None) -> list:
    """
    Analyze multiple spectrograms
    
    Args:
        image_paths: List of spectrogram image paths
        node_data: Optional list of dicts with node_id and location for each image
        
    Returns:
        List of analysis results
    """
    results = []
    node_data = node_data or [{}] * len(image_paths)
    
    for i, path in enumerate(image_paths):
        data = node_data[i] if i < len(node_data) else {}
        result = analyze_spectrogram(
            path,
            node_id=data.get('node_id', ''),
            location=(data.get('lat', 0), data.get('lon', 0))
        )
        results.append(result)
    
    return results


# =============================================================================
# ALERT ANALYSIS (Azure GPT-4o Text)
# =============================================================================

def analyze_alert(alert: dict, spectrogram_result: Optional[dict] = None) -> str:
    """
    Analyze an alert with optional spectrogram classification context
    
    Args:
        alert: Alert data dictionary
        spectrogram_result: Optional result from analyze_spectrogram()
        
    Returns:
        Analysis text
    """
    init_azure_client()
    
    if client is None:
        return "Unable to analyze: Azure AI service unavailable"
    
    # Build context with spectrogram results if available
    spec_context = ""
    if spectrogram_result and spectrogram_result.get('success'):
        spec_context = f"""
    
    SPECTROGRAM ANALYSIS (AI Vision):
    - Classification: {spectrogram_result.get('classification', 'unknown')}
    - Confidence: {spectrogram_result.get('confidence', 0)}%
    - Threat Level: {spectrogram_result.get('threat_level', 'UNKNOWN')}
    - Features: {', '.join(spectrogram_result.get('features_detected', []))}
    - AI Reasoning: {spectrogram_result.get('reasoning', '')}"""
    
    prompt = f"""You are a forest monitoring AI. An alert was received:
    - Anomaly Score: {alert.get('confidence', alert.get('anomaly_score', 0))}%
    - Location: {alert.get('lat', 0)}, {alert.get('lon', 0)}
    - Battery: {alert.get('battery', 0)}%
    - Node: {alert.get('node_id', '')}{spec_context}
    
    Provide a brief analysis and final threat assessment (Low/Medium/High/Critical).
    Consider both the anomaly detection and AI vision classification."""
    
    try:
        response = client.chat.completions.create(
            model=Config.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a concise forest monitoring assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Alert analysis failed: {e}")
        return f"Analysis unavailable: {str(e)}"


# =============================================================================
# DAILY REPORTS (Azure GPT-4o Text)
# =============================================================================

def generate_daily_report(alerts: list, spectrogram_analyses: list = None) -> str:
    """
    Generate a daily monitoring report
    
    Args:
        alerts: List of alert dictionaries
        spectrogram_analyses: Optional list of spectrogram analysis results
        
    Returns:
        Report text
    """
    init_azure_client()
    
    if client is None:
        return "Unable to generate report: Azure AI service unavailable"
    
    # Summarize spectrogram analyses
    spec_summary = ""
    if spectrogram_analyses:
        chainsaw_count = sum(1 for a in spectrogram_analyses if a.get('classification') == 'chainsaw')
        vehicle_count = sum(1 for a in spectrogram_analyses if a.get('classification') == 'vehicle')
        natural_count = sum(1 for a in spectrogram_analyses if a.get('classification') == 'natural')
        avg_confidence = sum(a.get('confidence', 0) for a in spectrogram_analyses) / len(spectrogram_analyses) if spectrogram_analyses else 0
        
        spec_summary = f"""
    
    SPECTROGRAM ANALYSIS SUMMARY:
    - Total Analyzed: {len(spectrogram_analyses)}
    - Chainsaw Detections: {chainsaw_count}
    - Vehicle Detections: {vehicle_count}
    - Natural Sounds: {natural_count}
    - Average AI Confidence: {avg_confidence:.1f}%"""
    
    prompt = f"""Summarize the last 24 hours of forest monitoring:
    
    ALERTS RECEIVED: {len(alerts)}
    {alerts[:20] if len(alerts) > 20 else alerts}
    {spec_summary}
    
    Include:
    1. Total alerts and confirmed threats
    2. High-risk areas (cluster analysis)
    3. Time patterns (peak activity hours)
    4. Recommendations for patrol routes
    5. Equipment status concerns"""
    
    try:
        response = client.chat.completions.create(
            model=Config.AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a forest protection analyst. Create concise, actionable reports."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return f"Report generation failed: {str(e)}"


# =============================================================================
# SMS/NOTIFICATION TEXT
# =============================================================================

def generate_sms_text(alert: dict, spectrogram_result: Optional[dict] = None) -> str:
    """Generate SMS alert text"""
    base_text = f"FOREST ALERT: "
    
    if spectrogram_result and spectrogram_result.get('classification') == 'chainsaw':
        confidence = spectrogram_result.get('confidence', 0)
        base_text += f"CHAINSAW CONFIRMED ({confidence}% conf) "
    else:
        base_text += "Anomaly detected "
    
    base_text += f"at ({alert.get('lat', 0):.4f}, {alert.get('lon', 0):.4f}). "
    base_text += f"Node: {alert.get('node_id', 'unknown')}"
    
    return base_text


def generate_alert_notification(alert: dict, spectrogram_result: Optional[dict] = None) -> dict:
    """Generate structured alert notification for multiple channels"""
    classification = spectrogram_result.get('classification', 'unknown') if spectrogram_result else 'unknown'
    threat_level = spectrogram_result.get('threat_level', 'UNKNOWN') if spectrogram_result else 'UNKNOWN'
    confidence = spectrogram_result.get('confidence', 0) if spectrogram_result else 0
    
    return {
        "title": f"Forest Guardian Alert - {threat_level}",
        "classification": classification,
        "threat_level": threat_level,
        "confidence": confidence,
        "location": {
            "lat": alert.get('lat', 0),
            "lon": alert.get('lon', 0)
        },
        "node_id": alert.get('node_id', ''),
        "timestamp": datetime.utcnow().isoformat(),
        "sms_text": generate_sms_text(alert, spectrogram_result),
        "requires_immediate_action": threat_level in ['CRITICAL', 'HIGH'],
        "spectrogram_analysis": spectrogram_result
    }
