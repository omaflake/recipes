# Recipe: neovim-research – reading, writing, analysis (neovim line)
# LaTeX (TeX Live, full) and Typst with a live PDF beside the editor: neovim compiles on every save (vimtex +
# latexmk; for Typst `typst watch`), zathura shows the PDF next to it and reloads it; SyncTeX jumps between text and
# PDF (Ctrl+click in zathura → the line in neovim). Plus Python for analysis, pandoc.
{ lib, pkgs, settings, ... }:

{
  networking.hostName = "neovim-research";
  omaflake.editor = "neovim";

  environment.systemPackages = with pkgs; [
    (python3.withPackages (ps: with ps; [ numpy pandas matplotlib jupyterlab ]))
    texliveFull                # latexmk, biber, chktex, latexindent, every package
    texlab                     # LaTeX language server
    typst tinymist             # Typst and its language server
    zathura
    pandoc
  ];

  home-manager.users.${settings.user} = {
    # zathura in the desktop's colours, SyncTeX on; it reloads a PDF when it changes
    programs.zathura = {
      enable = true;
      options = {
        synctex = true;
        recolor = true;
        recolor-keephue = true;
        default-bg = "#1e1e2e";
        recolor-darkcolor = "#cdd6f4";
        recolor-lightcolor = "#1e1e2e";
        selection-clipboard = "clipboard";
      };
    };

    programs.neovim = {
      plugins = with pkgs.vimPlugins; [ vimtex nvim-lspconfig ];
      initLua = lib.mkAfter ''
        -- research: LaTeX with vimtex, Typst with typst watch – both with zathura beside the editor
        vim.g.vimtex_view_method = "zathura"
        vim.g.vimtex_compiler_latexmk = { continuous = 1 }   -- compiles on every save
        vim.g.vimtex_quickfix_open_on_warning = 0
        -- Open a .tex file and press <space>ll: compile continuously and open the PDF; <space>lv jumps to the
        -- cursor's place in the PDF; Ctrl+click in zathura jumps back

        -- Typst: <space>tp starts `typst watch` for this file and opens its PDF in zathura
        vim.keymap.set("n", "<leader>tp", function()
          local src = vim.fn.expand("%:p")
          local pdf = vim.fn.expand("%:p:r") .. ".pdf"
          vim.fn.jobstart({ "typst", "watch", src, pdf }, { detach = true })
          vim.defer_fn(function() vim.fn.jobstart({ "zathura", pdf }, { detach = true }) end, 1500)
        end, { desc = "Typst: live PDF in zathura" })

        -- Language servers: texlab (LaTeX), tinymist (Typst)
        vim.lsp.enable({ "texlab", "tinymist" })
      '';
    };
  };
}
