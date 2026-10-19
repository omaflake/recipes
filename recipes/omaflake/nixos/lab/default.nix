# Recipe: lab – omaflake's development recipe
# Everything to check the Mac integrations (camera, sound, microphone, clipboard, 3D) plus debug tools.
# The other recipes stay without these. Network, sharing, ephemeral mode and the integrations' defaults
# come from recipe.toml next to this file.
{ pkgs, ... }:

let
  python = pkgs.python3.withPackages (ps: [ ps.pygobject3 ]);

  # "omaflake Test" (Cmd+D → fuzzel): camera, sound, microphone, status
  omaflakeTest = pkgs.stdenvNoCC.mkDerivation {
    pname = "omaflake-test";
    version = "1";
    src = ./omaflake-test.py;
    dontUnpack = true;
    nativeBuildInputs = [ pkgs.wrapGAppsHook4 pkgs.gobject-introspection ];
    buildInputs = [ pkgs.gtk4 ];
    installPhase = ''
      install -Dm755 $src $out/bin/omaflake-test
      substituteInPlace $out/bin/omaflake-test --replace-fail '"""omaflake Test' '#!${python}/bin/python3
      """omaflake Test'
      install -Dm644 ${desktopItem}/share/applications/*.desktop -t $out/share/applications
    '';
    preFixup = ''
      # GTK's Vulkan renderer finds no device under virgl (like mpv, plan B39) – use its OpenGL renderer
      gappsWrapperArgs+=(--prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.mpv pkgs.pipewire pkgs.pulseaudio pkgs.systemd ]}
                         --set-default GSK_RENDERER ngl)
    '';
  };

  desktopItem = pkgs.makeDesktopItem {
    name = "omaflake-test";
    desktopName = "omaflake Test";
    comment = "Check camera, sound and microphone from the Mac";
    exec = "omaflake-test";
    icon = "camera-web";
    categories = [ "Utility" ];
  };
in
{
  networking.hostName = "lab";

  environment.systemPackages = [ omaflakeTest ] ++ (with pkgs; [
    # media: camera, sound, microphone
    v4l-utils mpv ffmpeg pavucontrol pulseaudio alsa-utils
    # graphics
    mesa-demos vulkan-tools wayland-utils
    # clipboard, screenshots
    wl-clipboard grim slurp
    # system
    htop strace lsof pciutils usbutils file jq
  ]);
}
