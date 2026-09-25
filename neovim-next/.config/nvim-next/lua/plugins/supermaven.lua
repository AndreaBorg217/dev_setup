-- Keep AI inline suggestions, which native keyword and LSP completion do not provide.
vim.pack.add({ "https://github.com/supermaven-inc/supermaven-nvim" }, { confirm = false })

require("supermaven-nvim").setup({ disable_keymaps = true })

-- Keep native LSP snippet navigation ahead of Supermaven's conditional Tab acceptance.
vim.keymap.set(
	"i",
	"<Tab>",
	function()
		if vim.snippet.active({ direction = 1 }) then
			vim.snippet.jump(1)
		else
			require("supermaven-nvim.completion_preview").on_accept_suggestion()
		end
	end,
	{ desc = "Jump through snippet, accept Supermaven, or insert tab" }
)
