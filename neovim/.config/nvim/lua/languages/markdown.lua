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
	on_attach = function(client, bufnr)
		vim.lsp.completion.enable(true, client.id, bufnr, { autotrigger = true })
	end,
})

vim.lsp.enable("marksman")

local format = require("languages.lsp.format")

local function format_markdown(bufnr)
	local before = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
	local input = table.concat(before, "\n") .. "\n"
	local after = vim.fn.systemlist({ "prettier", "--stdin-filepath", vim.api.nvim_buf_get_name(bufnr) }, input)
	if vim.v.shell_error ~= 0 then
		vim.notify("Prettier could not format this Markdown file", vim.log.levels.ERROR)
		return
	end
	format.apply_diff(bufnr, after)
end

format.format_on_save("markdown", format_markdown)
