"""
azure_ml_train.py - Train model on Azure ML (Forest Guardian)

Configuration is loaded from ml/.env file.
See ml/.env.example for required variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from azureml.core import Workspace, Experiment, ScriptRunConfig, Environment
from azureml.core.compute import ComputeTarget, AmlCompute
from azureml.core.authentication import InteractiveLoginAuthentication


def get_workspace() -> Workspace:
    """Get Azure ML workspace from environment variables or config file."""
    subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
    resource_group = os.getenv('AZURE_RESOURCE_GROUP')
    workspace_name = os.getenv('AZURE_ML_WORKSPACE_NAME')
    
    if subscription_id and resource_group and workspace_name:
        print(f"Connecting to workspace: {workspace_name}")
        return Workspace(
            subscription_id=subscription_id,
            resource_group=resource_group,
            workspace_name=workspace_name
        )
    else:
        print("Using config.json for workspace connection...")
        return Workspace.from_config()


def main():
    # Check for required environment variables
    if not os.getenv('AZURE_SUBSCRIPTION_ID'):
        print("=" * 60)
        print("WARNING: Azure ML environment variables not set.")
        print(f"Please configure: {env_path}")
        print("=" * 60)
    
    ws = get_workspace()
    print(f"Connected to workspace: {ws.name}")
    
    # Get compute configuration from environment
    compute_name = os.getenv('AZURE_COMPUTE_NAME', 'cpu-cluster')
    vm_size = os.getenv('AZURE_VM_SIZE', 'STANDARD_DS2_V2')
    max_nodes = int(os.getenv('AZURE_MAX_NODES', '2'))
    
    if compute_name in ws.compute_targets:
        compute_target = ws.compute_targets[compute_name]
        print(f"Using existing compute: {compute_name}")
    else:
        print(f"Creating compute cluster: {compute_name} ({vm_size}, max {max_nodes} nodes)")
        compute_config = AmlCompute.provisioning_configuration(
            vm_size=vm_size,
            max_nodes=max_nodes
        )
        compute_target = ComputeTarget.create(ws, compute_name, compute_config)
        compute_target.wait_for_completion(show_output=True)

    env = Environment.from_conda_specification(
        name="forest-guardian-env",
        file_path=str(Path(__file__).parent.parent / 'requirements.txt')
    )

    src = ScriptRunConfig(
        source_directory=str(Path(__file__).parent),
        script='train.py',
        compute_target=compute_target,
        environment=env
    )

    exp = Experiment(ws, 'forest-guardian-train')
    run = exp.submit(src)
    run.wait_for_completion(show_output=True)
    print("Azure ML training complete.")

if __name__ == "__main__":
    main()
