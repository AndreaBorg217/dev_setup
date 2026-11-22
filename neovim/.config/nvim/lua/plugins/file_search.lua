-- Keep live project pickers and previews without the optional sorter or icon plugins.
vim.pack.add({ "https://github.com/nvim-telescope/telescope.nvim" }, { confirm = false })

require("telescope").setup({
	defaults = {
		path_display = { truncate = false },
		-- Preview below the results so long paths get the full window width.
		layout_strategy = "vertical",
		layout_config = {
			width = 0.99,
			height = 0.99,
			-- The default cutoff hides the preview in windows under 40 lines tall.
			vertical = { preview_height = 0.4, preview_cutoff = 0 },
		},
	},
})
local builtin = require("telescope.builtin")

-- --hidden would otherwise list VCS internals and untracked dependency trees.
local excluded_globs = {}
for _, dir in ipairs({ ".git", "node_modules", ".venv", "venv", "__pycache__", "target", ".idea" }) do
	vim.list_extend(excluded_globs, { "--glob", "!**/" .. dir .. "/**" })
end

-- The global 'autocomplete' option (options.lua) would otherwise pop native
-- completion over the prompt as you type a query.
vim.api.nvim_create_autocmd("FileType", {
	group = vim.api.nvim_create_augroup("telescope_prompt_no_autocomplete", { clear = true }),
	pattern = "TelescopePrompt",
	callback = function()
		vim.bo.autocomplete = false
	end,
})

local function project_root()
	return vim.fs.root(0, ".git") or vim.uv.cwd()
end

vim.keymap.set("n", "<leader>ff", function()
	builtin.find_files({
		cwd = project_root(),
		find_command = vim.list_extend({ "rg", "--files", "--color", "never", "--hidden" }, excluded_globs),
	})
end, { desc = "Find project files" })

vim.keymap.set("n", "<leader>fs", function()
	builtin.live_grep({ cwd = project_root(), additional_args = vim.list_extend({ "--hidden" }, excluded_globs) })
end, { desc = "Search project text" })

vim.keymap.set("n", "<leader>fk", builtin.keymaps, { desc = "Find keymaps" })
vim.keymap.set("n", "<leader>fd", function()
	builtin.diagnostics({ line_width = "full" })
end, { desc = "Find diagnostics" })
