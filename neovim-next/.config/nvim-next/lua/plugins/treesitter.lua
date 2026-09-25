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
