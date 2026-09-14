return {
   "folke/which-key.nvim",
   event = "VeryLazy",
   init = function()
     vim.o.timeout = true
     vim.o.timeoutlen = 500
   end,
   opts = {
      -- your configuration comes here
      -- or leave it empty to use the default settings
      -- refer to the configuration section below
    },
   config = function(_, opts)
      require("which-key").setup(opts)
      require("which-key").add({
         { "<leader>c", group = "copy/code" },
         { "<leader>d", group = "debug" },
         { "<leader>e", group = "explorer" },
         { "<leader>f", group = "find/format" },
         { "<leader>g", group = "lsp/goto" },
         { "<leader>h", group = "harpoon" },
         { "<leader>l", group = "lint/lazygit" },
         { "<leader>o", group = "open/organise" },
         { "<leader>s", group = "split" },
         { "<leader>t", group = "tab" },
         { "<leader>x", group = "diagnostics" },
      })
   end,
}
