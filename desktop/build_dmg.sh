#!/usr/bin/env bash
set -euo pipefail

app="${1:?Usage: build_dmg.sh PATH_TO_APP PATH_TO_DMG}"
image="${2:?Usage: build_dmg.sh PATH_TO_APP PATH_TO_DMG}"
scratch=$(mktemp -d "${TMPDIR:-/tmp}/neurodaily-dmg.XXXXXX")
mount_dir="$scratch/mount"
staging="$scratch/staging"
mounted=false

cleanup() {
  if "$mounted" && ! hdiutil detach "$mount_dir" -force >/dev/null; then
    return 1
  fi
  rm -rf -- "$scratch"
}
trap cleanup EXIT

mkdir "$mount_dir" "$staging"
mkdir -p "$(dirname "$image")"
ditto "$app" "$staging/NeuroDaily.app"
ln -s /Applications "$staging/Applications"
icon=$(plutil -extract CFBundleIconFile raw "$app/Contents/Info.plist")
cp "$app/Contents/Resources/${icon%.icns}.icns" "$staging/.VolumeIcon.icns"

hdiutil create -quiet -srcfolder "$staging" -fs HFS+ -volname NeuroDaily -format UDRW "$scratch/staging.dmg"
hdiutil attach -quiet -nobrowse -noautoopen -mountpoint "$mount_dir" "$scratch/staging.dmg"
mounted=true
SetFile -a C "$mount_dir"
hdiutil detach "$mount_dir" || hdiutil detach -force "$mount_dir"
mounted=false
hdiutil convert "$scratch/staging.dmg" -format UDZO -o "$image"
hdiutil verify "$image"
