-- Keep a project-specific ordered file list for direct numbered navigation.
vim.pack.add({ "https://github.com/ThePrimeagen/harpoon" }, { confirm = false })

local mark = require("harpoon.mark")
local ui = require("harpoon.ui")

vim.keymap.set("n", "<leader>ha", mark.add_file, { desc = "Harpoon: add file" })
vim.keymap.set("n", "<leader>hc", mark.clear_all, { desc = "Harpoon: clear files" })
vim.keymap.set("n", "<leader>hd", mark.rm_file, { desc = "Harpoon: remove file" })
vim.keymap.set("n", "<leader>hh", ui.toggle_quick_menu, { desc = "Harpoon: toggle quick menu" })
vim.keymap.set("n", "<leader>hn", ui.nav_next, { desc = "Harpoon: next file" })
vim.keymap.set("n", "<leader>hp", ui.nav_prev, { desc = "Harpoon: previous file" })

for index = 1, 4 do
	local file_index = index
	vim.keymap.set("n", "<leader>h" .. index, function()
		ui.nav_file(file_index)
	end, { desc = "Harpoon: go to file " .. index })
end
