-- Run :Copilot auth

return {
	{
		"zbirenbaum/copilot.lua",
		cmd = "Copilot",
		event = "InsertEnter",
		config = function()
			require("copilot").setup({
				-- panel = {
				--   enabled = true,
				--   auto_refresh = false,
				--   keymap = {
				--     jump_prev = "[[",
				--     jump_next = "]]",
				--     accept = "<CR>",
				--     refresh = "gr",
				--     open = "<M-CR>"
				--   },
				--   layout = {
				--     position = "bottom",
				--     ratio = 0.4
				--   },
				-- },
				suggestion = {
					enabled = true,
					auto_trigger = true,
					hide_during_completion = true,
					debounce = 75,
					keymap = {
						accept = false, -- We'll handle this with a custom keymap
						-- dismiss = "<C-x>",
						-- accept_word = "<C-w>",
						-- accept_line = "<C-l>",
						-- next = "<M-]>",
						-- prev = "<M-[>",
					},
				},
				-- filetypes = {
				--   yaml = false,
				--   markdown = false,
				--   help = false,
				--   gitcommit = false,
				--   gitrebase = false,
				--   hgcommit = false,
				--   svn = false,
				--   cvs = false,
				--   ["."] = false,
				-- },
			})

			-- Custom Tab mapping: accept Copilot suggestion if available, otherwise insert tab
			vim.keymap.set("i", "<Tab>", function()
				local suggestion = require("copilot.suggestion")
				if suggestion.is_visible() then
					suggestion.accept()
				else
					vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Tab>", true, false, true), "n", false)
				end
			end, { desc = "Accept Copilot suggestion or insert tab" })
		end,
	},
	{
		"CopilotC-Nvim/CopilotChat.nvim",
		dependencies = {
			{ "zbirenbaum/copilot.lua" },
			{ "nvim-lua/plenary.nvim" },
		},
		build = "make tiktoken",
		opts = {
			debug = false,
		},
		keys = {
			{
				"<leader>cc",
				function()
					require("CopilotChat").toggle()
				end,
				desc = "CopilotChat - Toggle",
			},
			{
				"<leader>ccr",
				function()
					require("CopilotChat").reset()
				end,
				desc = "CopilotChat - Reset",
			},
		},
	},
}
