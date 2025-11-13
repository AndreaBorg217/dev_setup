return {
	"ThePrimeagen/harpoon",
	config = function()
		local mark = require("harpoon.mark")
		local ui = require("harpoon.ui")

		local keymap = vim.keymap

		keymap.set("n", "<leader>ha", function()
			mark.add_file()
		end, { desc = "Harpoon: add file" })

		keymap.set("n", "<leader>hc", function()
			mark.clear_all()
		end, { desc = "Harpoon: clear files" })

		keymap.set("n", "<leader>hd", function()
			mark.rm_file()
		end, { desc = "Harpoon: delete file" })

		keymap.set("n", "<leader>hh", function()
			ui.toggle_quick_menu()
		end, { desc = "Harpoon: toggle quick menu" })

		keymap.set("n", "<leader>hn", function()
			ui.nav_next()
		end, { desc = "Harpoon: next mark" })
		keymap.set("n", "<leader>hp", function()
			ui.nav_prev()
		end, { desc = "Harpoon: previous mark" })

		keymap.set("n", "<leader>h1", function()
			ui.nav_file(1)
		end, { desc = "Harpoon: go to mark 1" })
		keymap.set("n", "<leader>h2", function()
			ui.nav_file(2)
		end, { desc = "Harpoon: go to mark 2" })
		keymap.set("n", "<leader>h3", function()
			ui.nav_file(3)
		end, { desc = "Harpoon: go to mark 3" })
		keymap.set("n", "<leader>h4", function()
			ui.nav_file(4)
		end, { desc = "Harpoon: go to mark 4" })
	end,
}
