-- Highlight TODO keywords in comments and search them with the configured aliases.
vim.pack.add({ "https://github.com/folke/todo-comments.nvim" }, { confirm = false })

require("todo-comments").setup({})
vim.keymap.set("n", "<leader>ft", "<cmd>TodoTelescope<CR>", { desc = "Find TODO comments" })
