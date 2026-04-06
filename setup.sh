#!/usr/bin/env bash
set -euo pipefail

echo "=== Instagram Carousel Maker — Setup ==="
echo ""

# Create dirs
mkdir -p assets/fonts data/slides

# Install Python deps
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Download fonts from official GitHub sources
echo ""
echo "Downloading fonts..."

BASE_M="https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf"

curl -sL "$BASE_M/Montserrat-ExtraBold.ttf" -o assets/fonts/Montserrat-ExtraBold.ttf
echo "  ✓ Montserrat-ExtraBold.ttf"

curl -sL "$BASE_M/Montserrat-Bold.ttf" -o assets/fonts/Montserrat-Bold.ttf
echo "  ✓ Montserrat-Bold.ttf"

# Use Montserrat-Regular for body text (reliable source)
curl -sL "$BASE_M/Montserrat-Regular.ttf" -o assets/fonts/Inter-Regular.ttf
echo "  ✓ Inter-Regular.ttf (Montserrat Regular)"

# NotoEmoji for emoji rendering (monochrome, cross-platform)
curl -sL "https://raw.githubusercontent.com/google/fonts/main/ofl/notoemoji/NotoEmoji%5Bwght%5D.ttf" \
  -o assets/fonts/NotoEmoji-Regular.ttf
echo "  ✓ NotoEmoji-Regular.ttf"

echo ""
echo "Font sizes:"
ls -lh assets/fonts/

# Verify Pillow works
echo ""
echo "Verifying Pillow..."
python3 -c "
from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGB', (100, 100), (8, 8, 16))
print('  Pillow OK —', Image.__version__)
"

# Copy .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from .env.example — fill in your credentials!"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your Gemini API key + Instagram credentials"
echo "  2. Test render (no posting): DRY_RUN=true python main.py"
echo "  3. Check data/slides/ to preview your carousel"
echo "  4. Real post: python main.py"
echo "  5. Push to GitHub + add secrets for automated daily posting"
echo ""
