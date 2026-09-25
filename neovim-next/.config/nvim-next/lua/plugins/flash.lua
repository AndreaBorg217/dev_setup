-- Labelled `s` jumps reach visible text directly; Neovim has no native equivalent.
vim.pack.add({ "https://github.com/folke/flash.nvim" }, { confirm = false })

require("flash").setup({})
vim.api.nvim_set_hl(0, "FlashLabel", { fg = "#ffffff", bg = "#b42336", bold = true })
vim.keymap.set({ "n", "x", "o" }, "s", function()
	require("flash").jump()
end, { desc = "Flash jump" })
vim.keymap.set({ "n", "x", "o" }, "S", function()
	require("flash").treesitter()
end, { desc = "Select Treesitter node with Flash" })
