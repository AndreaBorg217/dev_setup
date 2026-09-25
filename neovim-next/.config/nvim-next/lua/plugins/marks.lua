-- Native marks are invisible; show them in the sign column without extra mappings.
vim.pack.add({ "https://github.com/chentoast/marks.nvim" }, { confirm = false })

require("marks").setup({
	default_mappings = false, -- Keep Neovim's native mark commands and avoid unused shortcuts.
})
