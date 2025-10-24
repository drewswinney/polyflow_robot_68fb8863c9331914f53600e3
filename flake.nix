{
  inputs = {
    nix-ros-overlay.url = "github:lopsided98/nix-ros-overlay/master";
    # Ensure nixpkgs follows nix-ros-overlay's version to avoid compatibility issues
    nixpkgs.follows = "nix-ros-overlay/nixpkgs"; 
  };

  outputs = { self, nixpkgs, nix-ros-overlay, ... }@inputs:
    let 
      ros-pkgs = nixpkgs.legacyPackages.aarch64-linux.extend nix-ros-overlay.overlays.default;
    in { 
      nixosConfigurations."68fb8863c9331914f53600e3" = nixpkgs.lib.nixosSystem {
          system = "aarch64-linux";
          specialArgs = { inherit ros-pkgs; };
          modules = [
            # Base NixOS modules
            ./configuration.nix
          ];
          # Further configuration specific to your Raspberry Pi and ROS needs
        };
        substituters = https://ros.cachix.org;
        trusted-public-keys = cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY= ros.cachix.org-1:dSyZxI8geDCJrwgvCOHDoAfOm5sV1wCPjBkKL+38Rvo=;
    };
}