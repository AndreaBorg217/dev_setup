return {
	"folke/trouble.nvim",
	dependencies = { "nvim-tree/nvim-web-devicons", "folke/todo-comments.nvim" },
	opts = {
		focus = true,
	},
	cmd = "Trouble",
	keys = {
		{ "<leader>xw", "<cmd>Trouble diagnostics open<CR>", desc = "Open trouble workspace diagnostics" },
		{ "<leader>fd", "<cmd>Telescope diagnostics<CR>", desc = "Telescope diagnostics" },
	},
}
