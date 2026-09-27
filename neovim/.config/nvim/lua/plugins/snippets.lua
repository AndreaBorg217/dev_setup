vim.pack.add({
	"https://github.com/nvim-mini/mini.snippets",
	"https://github.com/rafamadriz/friendly-snippets",
}, { confirm = false })

local snippets = require("mini.snippets")
snippets.setup({ snippets = { snippets.gen_loader.from_lang() } })

vim.api.nvim_create_autocmd("LspAttach", {
	callback = function(args)
		local client = vim.lsp.get_client_by_id(args.data.client_id)
		if client.name == "mini.snippets" then
			vim.lsp.completion.enable(true, client.id, args.buf, { autotrigger = true })
		end
	end,
})

local languages = { java = true, python = true, go = true }
snippets.start_lsp_server({
	match = false,
	before_attach = function(bufnr)
		return languages[vim.bo[bufnr].filetype] == true
	end,
})
