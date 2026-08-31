return {
	"nvim-telescope/telescope.nvim",
	tag = "v0.1.9",
	dependencies = {
		"nvim-lua/plenary.nvim",
		{ "nvim-telescope/telescope-fzf-native.nvim", build = "make" },
		"nvim-tree/nvim-web-devicons",
		"folke/todo-comments.nvim",
	},
	config = function()
		local telescope = require("telescope")
		local actions = require("telescope.actions")
		local transform_mod = require("telescope.actions.mt").transform_mod
		local generated_path_globs = {
			"!**/.git/**",
			"!**/.venv/**",
			"!**/node_modules/**",
			"!**/__pycache__/**",
			"!**/.pytest_cache/**",
			"!**/.mypy_cache/**",
			"!**/.ruff_cache/**",
			"!**/.tox/**",
			"!**/.gradle/**",
			"!**/target/**",
			"!**/build/**",
			"!**/dist/**",
			"!**/coverage/**",
			"!**/htmlcov/**",
			"!**/.coverage",
		}

		local function generated_path_arguments()
			local arguments = {}
			for _, path_glob in ipairs(generated_path_globs) do
				table.insert(arguments, "--glob")
				table.insert(arguments, path_glob)
			end

			return arguments
		end

		local find_files_command = { "rg", "--files", "--hidden", "--no-ignore" }
		vim.list_extend(find_files_command, generated_path_arguments())

		local trouble = require("trouble")
		local trouble_telescope = require("trouble.sources.telescope")

		-- or create your custom action
		local custom_actions = transform_mod({
			open_trouble_qflist = function(prompt_bufnr)
				trouble.toggle("quickfix")
			end,
		})

		telescope.setup({
			defaults = {
				path_display = { "smart" },
				mappings = {
					i = {
						["<C-k>"] = actions.move_selection_previous, -- move to prev result
						["<C-j>"] = actions.move_selection_next, -- move to next result
						["<C-q>"] = actions.send_selected_to_qflist + custom_actions.open_trouble_qflist,
						["<C-t>"] = trouble_telescope.open,
					},
				},
			},
			pickers = {
				find_files = {
					find_command = find_files_command,
				},
				live_grep = {
					additional_args = function()
						local arguments = { "--hidden", "--no-ignore" }
						return vim.list_extend(arguments, generated_path_arguments())
					end,
				},
			},
		})

		telescope.load_extension("fzf")

		-- set keymaps
		local keymap = vim.keymap -- for conciseness

		keymap.set("n", "<leader>ff", "<cmd>Telescope find_files<cr>", { desc = "Find files in project" })
		keymap.set("n", "<leader>fs", "<cmd>Telescope live_grep<cr>", { desc = "Find string in project" })
		keymap.set("n", "<leader>ft", "<cmd>TodoTelescope<cr>", { desc = "Find todos" })
		keymap.set("n", "<leader>fk", "<cmd>Telescope keymaps<cr>", { desc = "Find keymaps" })
	end,
}
