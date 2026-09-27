-- Labelled `s` jumps reach visible text directly; Neovim has no native equivalent.
vim.pack.add({ "https://github.com/folke/flash.nvim" }, { confirm = false })

require("flash").setup({
	-- `s`: single-char jumps only. Once the pattern reaches this length, stop
	-- excluding labels that would otherwise be ambiguous with continuing to
	-- type the search pattern, so a single character always gets the full
	-- label alphabet. Typing past this length forces a jump/terminate
	-- instead of narrowing further.
	search = { max_length = 1 },
	modes = {
		-- `/` and `?`: label matches during regular search, where multi-char
		-- patterns are the norm and narrowing before jumping is expected, so
		-- restore full incremental patterns here instead of the 1-char cap.
		search = {
			enabled = true,
			search = { max_length = false },
		},
	},
})
vim.api.nvim_set_hl(0, "FlashLabel", { fg = "#ffffff", bg = "#b42336", bold = true })
vim.keymap.set({ "n", "x", "o" }, "s", function()
	require("flash").jump()
end, { desc = "Flash jump" })
vim.keymap.set({ "n", "x", "o" }, "S", function()
	require("flash").treesitter()
end, { desc = "Select Treesitter node with Flash" })
