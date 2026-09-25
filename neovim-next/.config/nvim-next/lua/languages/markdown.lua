vim.api.nvim_create_autocmd("FileType", {
	group = vim.api.nvim_create_augroup("prose_spelling", { clear = true }),
	pattern = { "markdown", "text" },
	callback = function()
		-- Highlight British spelling in prose without an extra lint plugin.
		vim.opt_local.spell = true
		vim.opt_local.spelllang = "en_gb"
	end,
})

-- Marksman adds Markdown link completion, references, and link diagnostics.
vim.lsp.config("marksman", {
	cmd = { "marksman", "server" },
	filetypes = { "markdown", "markdown.mdx" },
	root_markers = { ".marksman.toml", ".git" },
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
	end,
})

vim.lsp.enable("marksman")

local function format_markdown(bufnr)
	local before = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
	local input = table.concat(before, "\n") .. "\n"
	local after = vim.fn.systemlist({ "prettier", "--stdin-filepath", vim.api.nvim_buf_get_name(bufnr) }, input)
	if vim.v.shell_error ~= 0 then
		vim.notify("Prettier could not format this Markdown file", vim.log.levels.ERROR)
		return
	end

	-- Apply changed hunks only, keeping diagnostics on untouched lines in place.
	local hunks = vim.diff(input, table.concat(after, "\n") .. "\n", { result_type = "indices" })
	for index = #hunks, 1, -1 do
		local hunk = hunks[index]
		local start = hunk[1] - (hunk[2] > 0 and 1 or 0)
		local replacement = {}
		for line = hunk[3], hunk[3] + hunk[4] - 1 do
			table.insert(replacement, after[line])
		end
		vim.api.nvim_buf_set_lines(bufnr, start, start + hunk[2], false, replacement)
	end
end

vim.api.nvim_create_autocmd("FileType", {
	group = vim.api.nvim_create_augroup("markdown_format", { clear = true }),
	pattern = "markdown",
	callback = function(args)
		vim.keymap.set("n", "<leader>fmt", function()
			format_markdown(args.buf)
		end, { buffer = args.buf, desc = "Format Markdown file" })
		vim.api.nvim_create_autocmd("BufWritePre", {
			group = vim.api.nvim_create_augroup("markdown_format_" .. args.buf, { clear = true }),
			buffer = args.buf,
			callback = function()
				if require("config").AUTO_FORMAT then
					format_markdown(args.buf)
				end
			end,
		})
	end,
})
