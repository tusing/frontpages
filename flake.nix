{
  description = "A simple Flask app to serve frontpages of newspapers as images for e-ink displays";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs, flake-utils }: flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = nixpkgs.legacyPackages.${system};

      # Define python packages for our app
      pythonEnv = pkgs.python3.withPackages (ps: with ps; [
        flask
        flask-caching
        requests
        pdf2image
        pillow
        pyyaml
      ]);

      # Define the app
      app = pkgs.writeShellScriptBin "frontpages" ''
        export PATH="${pythonEnv}/bin:${pkgs.poppler_utils}/bin:$PATH"
        python3 frontpages.py
      '';

    in
    {
      defaultPackage = app;
      devShell = pkgs.mkShell {
        buildInputs = with pkgs; [ pythonEnv poppler_utils ];
        shellHook = ''
          export PATH="${pythonEnv}/bin:${pkgs.poppler_utils}/bin:$PATH"
        '';
      };
    });
}
