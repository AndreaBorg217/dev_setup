-- Keep live project pickers and previews without the optional sorter or icon plugins.
vim.pack.add({ "https://github.com/nvim-telescope/telescope.nvim" }, { confirm = false })

require("telescope").setup({})
local builtin = require("telescope.builtin")

local function project_root()
	return vim.fs.root(0, ".git") or vim.uv.cwd()
end

vim.keymap.set("n", "<leader>ff", function()
	builtin.find_files({ hidden = true, cwd = project_root() })
end, { desc = "Find project files" })

vim.keymap.set("n", "<leader>fs", function()
	builtin.live_grep({ cwd = project_root(), additional_args = { "--hidden" } })
end, { desc = "Search project text" })

vim.keymap.set("n", "<leader>fk", builtin.keymaps, { desc = "Find keymaps" })
vim.keymap.set("n", "<leader>fd", function()
	builtin.diagnostics({ line_width = "full" })
end, { desc = "Find diagnostics" })
