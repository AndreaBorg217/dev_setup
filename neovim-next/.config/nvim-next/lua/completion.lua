vim.keymap.set("i", "<CR>", function()
	if vim.fn.pumvisible() == 1 and vim.fn.complete_info({ "selected" }).selected >= 0 then
		return "<C-y>"
	end
	return "<CR>"
end, { desc = "Accept selected completion or insert newline", expr = true })
