# API Documentation Auto-Deployment Setup

This document explains the one-time setup required to enable automatic API documentation deployment from the faxbot repo to faxbot.net/api/v1.

## What it does

- 🔄 **Auto-triggers** on push to development branch when API files change
- 📝 **Generates** fresh OpenAPI spec from FastAPI code
- 🎨 **Builds** beautiful Redocly documentation with faxbot branding
- 🚀 **Deploys** to faxbot.net/api/v1 automatically
- 📱 **Creates** API landing page at faxbot.net/api/

## One-time setup (5 minutes)

### 1. Create deploy key for faxbot.net repo

```bash
# Generate SSH key pair
ssh-keygen -t ed25519 -C "faxbot-api-docs-deploy" -f ~/.ssh/faxbot_net_deploy_key

# Copy public key
cat ~/.ssh/faxbot_net_deploy_key.pub
```

### 2. Add deploy key to faxbot.net repo

1. Go to https://github.com/dmontgomery40/faxbot.net/settings/keys
2. Click "Add deploy key"
3. Title: `API Docs Auto-Deploy`
4. Paste the public key from step 1
5. ✅ Check "Allow write access"
6. Click "Add key"

### 3. Add private key to faxbot repo secrets

1. Go to https://github.com/dmontgomery40/faxbot/settings/secrets/actions
2. Click "New repository secret"
3. Name: `FAXBOT_NET_DEPLOY_TOKEN`
4. Value: Copy the private key:
   ```bash
   cat ~/.ssh/faxbot_net_deploy_key
   ```
5. Click "Add secret"

### 4. Test the workflow

Push any change to the development branch in the api/ directory, or manually trigger:

1. Go to https://github.com/dmontgomery40/faxbot/actions
2. Click "Generate and Deploy API Documentation"
3. Click "Run workflow" → "Run workflow"

## Results

After setup, every push to development branch will automatically:

- ✅ Generate fresh API docs at **faxbot.net/api/v1/**
- ✅ Create API index page at **faxbot.net/api/**
- ✅ Professional Redocly styling with faxbot branding
- ✅ Interactive API explorer with "Try it out" buttons
- ✅ Search functionality
- ✅ Mobile-responsive design

## Troubleshooting

**Workflow fails with "Permission denied":**
- Check that deploy key has write access enabled
- Verify private key was copied correctly to secrets

**No documentation generated:**
- Check that FastAPI app imports correctly
- Verify requirements.txt includes all dependencies

**Documentation looks broken:**
- Check browser console for errors
- Verify Redocly config is valid YAML

## File locations

- **Workflow:** `.github/workflows/api-docs.yml`
- **Generated docs:** `faxbot.net/api/v1/index.html`
- **API index:** `faxbot.net/api/index.html`
- **This setup guide:** `API_DOCS_SETUP.md`

## Maintenance

- ✅ **Zero maintenance** - fully automated
- ✅ **Always up-to-date** - syncs with latest API changes
- ✅ **Professional appearance** - matches faxbot.net branding
- ✅ **SEO optimized** - static HTML for fast loading