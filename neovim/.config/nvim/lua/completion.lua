vim.keymap.set("i", "<CR>", function()
	if vim.fn.pumvisible() == 1 and vim.fn.complete_info({ "selected" }).selected >= 0 then
		return "<C-y>"
	end
	return "<CR>"
end, { desc = "Accept selected completion or insert newline", expr = true })

-- Native completion merges servers in response order, so instant snippet replies would lead the menu.
-- Rank snippets last, then fuzzy score, then the server's sortText. Applied to every enable call
-- because a buffer keeps the cmp from whichever client enables completion first.
local snippet_kind = vim.lsp.protocol.CompletionItemKind.Snippet

local function rank(entry)
	local item = vim.tbl_get(entry, "user_data", "nvim", "lsp", "completion_item") or {}
	local sort_text = item.sortText ~= "" and item.sortText or nil
	return item.kind == snippet_kind and 1 or 0, entry._fuzzy_score or 0, sort_text or item.label or entry.word or ""
end

local function compare(a, b)
	local snippet_a, score_a, text_a = rank(a)
	local snippet_b, score_b, text_b = rank(b)
	if snippet_a ~= snippet_b then
		return snippet_a < snippet_b
	end
	if score_a ~= score_b then
		return score_a > score_b
	end
	return text_a < text_b
end

local enable = vim.lsp.completion.enable
---@diagnostic disable-next-line: duplicate-set-field
vim.lsp.completion.enable = function(enabled, client_id, bufnr, opts)
	opts = vim.tbl_extend("keep", opts or {}, { cmp = compare })
	return enable(enabled, client_id, bufnr, opts)
end
