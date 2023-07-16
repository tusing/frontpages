{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs.python3Packages; [
    pkgs.poppler_utils
    pkgs.python3
    flask
    pdf2image
    pillow
    pyyaml
    requests
  ];

  shellHook = ''
    echo "Entering nix-shell..."
    #export PATH="$PATH:${pkgs.poppler_utils}/bin"
    export FLASK_APP=frontpages.py
  '';
}
