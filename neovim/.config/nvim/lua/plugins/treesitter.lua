-- Install language parsers for Flash's `S` selection and native Treesitter features.
vim.pack.add({
	{
		src = "https://github.com/nvim-treesitter/nvim-treesitter",
		version = "main",
	},
}, { confirm = false })

-- Install missing parsers asynchronously; existing parsers are left alone.
require("nvim-treesitter").install({
	"python",
	"java",
	"go",
	"gomod",
	"gosum",
	"dockerfile",
	"json",
	"yaml",
	"bash",
	"markdown",
	"markdown_inline",
})

-- nvim-treesitter's main branch no longer auto-attaches highlighting like the
-- master branch did; start it explicitly wherever a parser is installed and
-- fall back to legacy regex syntax otherwise (pcall no-ops without a parser).
vim.api.nvim_create_autocmd("FileType", {
	group = vim.api.nvim_create_augroup("treesitter_highlight", { clear = true }),
	callback = function()
		pcall(vim.treesitter.start)
	end,
})
