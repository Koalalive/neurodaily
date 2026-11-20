#!/usr/bin/env bash
set -euo pipefail

app="${1:?Usage: build_dmg.sh PATH_TO_APP PATH_TO_DMG}"
image="${2:?Usage: build_dmg.sh PATH_TO_APP PATH_TO_DMG}"
scratch=$(mktemp -d "${TMPDIR:-/tmp}/neurodaily-dmg.XXXXXX")
mount_dir="$scratch/mount"
staging="$scratch/staging"
mounted=false
disk=""

detach_image() {
  local target="${disk:-$mount_dir}"
  hdiutil detach "$target" && return
  sleep 1
  hdiutil detach -force "$target"
}

cleanup() {
  if "$mounted" && ! detach_image >/dev/null; then
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
hdiutil attach -plist -nobrowse -noautoopen -mountpoint "$mount_dir" "$scratch/staging.dmg" > "$scratch/attach.plist"
mounted=true
# The first detach can unmount the volume yet leave the disk attached.
# Use the device so the retry still works after the mount point is gone.
disk=$(plutil -extract system-entities.0.dev-entry raw "$scratch/attach.plist")
SetFile -a C "$mount_dir"
detach_image
mounted=false
hdiutil convert "$scratch/staging.dmg" -format UDZO -o "$image"
hdiutil verify "$image"
