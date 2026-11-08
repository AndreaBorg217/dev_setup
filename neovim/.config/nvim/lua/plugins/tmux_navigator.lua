-- Neovim window commands cannot enter tmux panes; this plugin lets Ctrl-h/j/k/l cross that boundary.
vim.g.tmux_navigator_no_mappings = 1 -- Replace plugin mappings with described keymaps.
vim.pack.add({ "https://github.com/christoomey/vim-tmux-navigator" }, { confirm = false })

vim.keymap.set("n", "<C-h>", "<cmd>TmuxNavigateLeft<CR>", { desc = "Move to left split or tmux pane", silent = true })
vim.keymap.set("n", "<C-j>", "<cmd>TmuxNavigateDown<CR>", { desc = "Move to lower split or tmux pane", silent = true })
vim.keymap.set("n", "<C-k>", "<cmd>TmuxNavigateUp<CR>", { desc = "Move to upper split or tmux pane", silent = true })
vim.keymap.set("n", "<C-l>", "<cmd>TmuxNavigateRight<CR>", { desc = "Move to right split or tmux pane", silent = true })
vim.keymap.set(
	"n",
	[[<C-\>]],
	"<cmd>TmuxNavigatePrevious<CR>",
	{ desc = "Move to previous split or tmux pane", silent = true }
)
