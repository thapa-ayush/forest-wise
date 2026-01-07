# Azure Maps Setup Guide

This guide walks you through creating an Azure Maps account and adding the key to Forest Guardian.

## Step 1: Create Azure Maps Account

1. Go to the [Azure Portal](https://portal.azure.com)

2. Click **+ Create a resource**

3. Search for **"Azure Maps"** and select it

4. Click **Create**

5. Fill in the details:
   - **Subscription**: Select your Azure subscription
   - **Resource group**: `forest-guardian-rg` (or create new)
   - **Name**: `forest-guardian-maps`
   - **Region**: Choose closest to your location
   - **Pricing tier**: **Gen2** (recommended) or **Gen1 S0**

6. Click **Review + create**, then **Create**

7. Wait for deployment to complete (~1-2 minutes)

## Step 2: Get Your Subscription Key

1. Once deployed, click **Go to resource**

2. In the left menu, click **Authentication**

3. Under **Shared Key Authentication**, copy the **Primary Key**

   ![Azure Maps Keys](https://learn.microsoft.com/en-us/azure/azure-maps/media/how-to-manage-authentication/copy-key.png)

## Step 3: Add Key to Forest Guardian

1. SSH into your Raspberry Pi:
   ```bash
   ssh forestguardain@10.0.0.222
   ```

2. Edit the `.env` file:
   ```bash
   nano /home/forestguardain/forest-g/hub/.env
   ```

3. Find the `AZURE_MAPS_KEY` line and add your key:
   ```env
   AZURE_MAPS_KEY=your-primary-key-here
   ```

4. Save and exit (`Ctrl+X`, then `Y`, then `Enter`)

5. Restart the Flask app:
   ```bash
   cd /home/forestguardain/forest-g/hub
   pkill -f "python.*app.py"
   source venv/bin/activate
   python app.py &
   ```

## Step 4: Verify

1. Open the Forest Guardian dashboard: http://10.0.0.222:5000

2. Navigate to the **Map** page

3. You should see the Azure Maps dark theme map load

4. If nodes have GPS coordinates, they will appear as green markers

## Pricing Information

Azure Maps offers a generous free tier:

| Tier | Free Transactions/Month | Cost After Free Tier |
|------|------------------------|---------------------|
| Gen2 | 1,000 - 250,000 (varies by API) | Pay-as-you-go |
| Gen1 S0 | 25,000 map tiles | ~$0.50/1000 after |

For Forest Guardian's typical usage (a few hundred map loads per day), you'll likely stay within the free tier.

## Troubleshooting

### Map shows "Azure Maps Key Required" warning
- Verify the key is correctly added to `.env`
- Ensure there are no extra spaces around the key
- Restart the Flask app after changing `.env`

### Map loads but shows no markers
- Check that your nodes have valid GPS coordinates
- Verify the `/api/nodes` endpoint returns data with `lat` and `lon` fields
- GPS coordinates of `0, 0` are filtered out

### 401 Unauthorized errors in console
- The subscription key may be incorrect
- Verify you copied the **Primary Key** from the Authentication page
- Check the key hasn't been regenerated in Azure Portal

## Additional Resources

- [Azure Maps Documentation](https://learn.microsoft.com/en-us/azure/azure-maps/)
- [Azure Maps Pricing](https://azure.microsoft.com/en-us/pricing/details/azure-maps/)
- [Azure Maps Web SDK](https://learn.microsoft.com/en-us/azure/azure-maps/how-to-use-map-control)
