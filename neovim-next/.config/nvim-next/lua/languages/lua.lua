vim.lsp.config("lua_ls", {
	cmd = { "lua-language-server" },
	filetypes = { "lua" },
	root_markers = { ".luarc.json", ".luarc.jsonc", ".git" },
	settings = {
		Lua = {
			-- LuaLS needs to recognise Neovim's injected vim global.
			diagnostics = { globals = { "vim" } },
			runtime = { version = "LuaJIT" },
			workspace = { library = { vim.env.VIMRUNTIME } },
			hint = { enable = true },
			codeLens = { enable = true },
		},
	},
	on_attach = function(client, bufnr)
		vim.lsp.inlay_hint.enable(true, { bufnr = bufnr })
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
		vim.keymap.set("n", "<leader>fmt", function()
			vim.lsp.buf.format({ bufnr = bufnr, id = client.id })
		end, { buffer = bufnr, desc = "Format Lua file" })
	end,
})

vim.lsp.enable("lua_ls")

vim.api.nvim_create_autocmd("BufWritePre", {
	group = vim.api.nvim_create_augroup("lua_format", { clear = true }),
	pattern = "*.lua",
	callback = function(args)
		if require("config").AUTO_FORMAT and #vim.lsp.get_clients({ bufnr = args.buf, name = "lua_ls" }) > 0 then
			vim.lsp.buf.format({ bufnr = args.buf, name = "lua_ls", timeout_ms = 5000 })
		end
	end,
})
