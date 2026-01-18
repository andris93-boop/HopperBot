#!/bin/sh

# Load environment variables
if [ -f .env ]; then
    . .env
fi

# Create PNG directory if it doesn't exist
mkdir -p PNG

QUERY="SELECT id, name, logo FROM clubs WHERE logo IS NOT NULL AND logo != '';"

# Get all logos from clubs table
sqlite3 "$DATABASE_NAME" "$QUERY" | while IFS='|' read -r id name logo; do
    # Skip if logo is empty
    if [ -z "$logo" ]; then
        continue
    fi
    
    # Check if logo is a full URL or just a suffix
    case "$logo" in
        http://*|https://*)
            file=${logo##*/}
            url="$logo"
            ;;
        *)
            # Combine with LOGO_URL from environment
            url="${LOGO_URL}${logo}"
            file=${logo}
            ;;
    esac    
    
    echo "Processing club: $name (URL: $url)"
    if [ -f "PNG/${file}" ]; then
        echo "Logo already exists for: $name (ID: $id), skipping download."
        echo ""
        continue
    fi
    # Download the image
    echo "Downloading logo for: $name (ID: $id)"
    echo "URL: $url"
    
    # Download with original filename
    wget -q -O "PNG/$file" "$url" 
    
    if [ $? -eq 0 ]; then
        echo "✓ Saved to PNG directory"
    else
        echo "✗ Failed to download: $url"
        echo "$id $name $logo" >> failed_downloads.log
    fi
    
    echo ""
done

echo "Download complete! Images saved in PNG directory."
