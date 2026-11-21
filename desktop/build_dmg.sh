#!/usr/bin/env bash
set -euo pipefail

app="${1:?Usage: build_dmg.sh PATH_TO_APP PATH_TO_DMG}"
image="${2:?Usage: build_dmg.sh PATH_TO_APP PATH_TO_DMG}"
codesign --verify --deep --strict --verbose=2 "$app"
scratch=$(mktemp -d "${TMPDIR:-/tmp}/neurodaily-dmg.XXXXXX")
mount_dir="$scratch/mount"
staging="$scratch/staging"
mounted=false
disk=""

detach_image() {
  local target="${disk:-$mount_dir}" delay
  hdiutil detach "$target" && return
  for delay in 1 2 4 8 16; do
    sleep "$delay"
    if [[ -n "$disk" && ! -e "$disk" ]]; then
      return 0
    fi
    hdiutil detach -force "$target" && return
  done
  return 1
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
codesign --verify --deep --strict --verbose=2 "$mount_dir/NeuroDaily.app"
SetFile -a C "$mount_dir"
detach_image
mounted=false
hdiutil convert "$scratch/staging.dmg" -format UDZO -o "$image"
hdiutil verify "$image"
