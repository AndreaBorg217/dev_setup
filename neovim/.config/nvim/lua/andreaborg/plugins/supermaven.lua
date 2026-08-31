return {
	"supermaven-inc/supermaven-nvim",
	event = "InsertEnter",
	config = function()
		require("supermaven-nvim").setup({
			disable_keymaps = true,
		})

		local completion_preview = require("supermaven-nvim.completion_preview")
		local function feed_key(key)
			local termcodes = vim.api.nvim_replace_termcodes(key, true, false, true)
			vim.api.nvim_feedkeys(termcodes, "n", false)
		end

		vim.keymap.set("i", "<Tab>", function()
			if completion_preview.has_suggestion() then
				completion_preview.on_accept_suggestion()
			else
				feed_key("<Tab>")
			end
		end, {
			desc = "Accept Supermaven suggestion or insert tab",
			noremap = true,
			silent = true,
		})

		-- vim.keymap.set("i", "<BS>", function()
		-- 	if completion_preview.has_suggestion() then
		-- 		completion_preview.on_dispose_inlay()
		-- 	else
		-- 		feed_key("<BS>")
		-- 	end
		-- end, {
		-- 	desc = "Dismiss Supermaven suggestion or delete character",
		-- 	noremap = true,
		-- 	silent = true,
		-- })
	end,
}
