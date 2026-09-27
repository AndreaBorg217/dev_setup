-- Keep a left tree with current-file reveal and collapse actions behind the existing keys.
vim.g.loaded_netrw = 1 -- Prevent netrw from opening over nvim-tree.
vim.g.loaded_netrwPlugin = 1 -- Disable netrw's plugin commands and autocommands.
vim.pack.add({ "https://github.com/nvim-tree/nvim-tree.lua" }, { confirm = false })

local api = require("nvim-tree.api")
require("nvim-tree").setup({
	on_attach = function(buffer)
		api.config.mappings.default_on_attach(buffer)
		vim.keymap.set("n", "t", function()
			local node = api.tree.get_node_under_cursor()
			if node and node.nodes then
				api.node.open.edit()
			end
		end, { buffer = buffer, desc = "Toggle folder" })
	end,
	view = { side = "left" }, -- Keep the explorer on the left of editing windows.
	renderer = {
		icons = {
			glyphs = {
				folder = {
					arrow_closed = "", -- Use a slimmer arrow to represent closed directories.
					arrow_open = "", -- Point down when a directory is expanded.
				},
			},
		},
	},
})

-- Creating with `a` selects the file in the tree but leaves focus in the tree buffer.
api.events.subscribe(api.events.Event.FileCreated, function()
	vim.schedule(api.node.open.edit)
end)

vim.keymap.set("n", "<leader>ee", "<cmd>NvimTreeToggle<CR>", { desc = "Toggle file explorer" })
vim.keymap.set("n", "<leader>eo", "<cmd>NvimTreeFindFile<CR>", { desc = "Reveal current file in explorer" })
vim.keymap.set("n", "<leader>ec", "<cmd>NvimTreeCollapse<CR>", { desc = "Collapse file explorer" })
vim.keymap.set("n", "<Esc>", function()
	if api.tree.is_visible() then
		api.tree.close()
	else
		vim.cmd.nohlsearch()
	end
end, { desc = "Close file explorer or clear search highlights" })
