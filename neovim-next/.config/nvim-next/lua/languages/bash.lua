vim.lsp.config("bashls", {
	cmd = { "bash-language-server", "start" },
	filetypes = { "sh", "bash" },
	root_markers = { ".git" },
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
		vim.keymap.set("n", "<leader>fmt", function()
			vim.lsp.buf.format({ bufnr = bufnr, id = client.id })
		end, { buffer = bufnr, desc = "Format Bash file" })
		vim.api.nvim_create_autocmd("BufWritePre", {
			group = vim.api.nvim_create_augroup("bash_format_" .. bufnr, { clear = true }),
			buffer = bufnr,
			callback = function()
				if require("config").AUTO_FORMAT then
					vim.lsp.buf.format({ bufnr = bufnr, id = client.id, timeout_ms = 5000 })
				end
			end,
		})
	end,
})

vim.lsp.enable("bashls")
