vim.lsp.config("jsonls", {
	init_options = { provideFormatter = true },
	settings = { json = { validate = { enable = true }, schemas = require("schemastore").json.schemas() } },
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
		vim.keymap.set("n", "<leader>fmt", function()
			vim.lsp.buf.format({ bufnr = bufnr, id = client.id })
		end, { buffer = bufnr, desc = "Format JSON file" })
	end,
})

vim.lsp.enable("jsonls")

vim.api.nvim_create_autocmd("BufWritePre", {
	group = vim.api.nvim_create_augroup("json_format", { clear = true }),
	pattern = { "*.json", "*.jsonc" },
	callback = function(args)
		if require("config").AUTO_FORMAT and #vim.lsp.get_clients({ bufnr = args.buf, name = "jsonls" }) > 0 then
			vim.lsp.buf.format({ bufnr = args.buf, name = "jsonls", timeout_ms = 5000 })
		end
	end,
})
