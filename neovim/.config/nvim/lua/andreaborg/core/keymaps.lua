local keymap = vim.keymap -- for conciseness

keymap.set("i", "jk", "<ESC>", { desc = "Exit insert mode with jk" })

keymap.set("n", "<leader>cs", ":nohl<CR>", { desc = "Clear search highlights" })

-- Untab with shift+tab in all modes
vim.keymap.set("i", "<S-Tab>", "<C-d>", { noremap = true, silent = true })
vim.keymap.set("v", "<S-Tab>", "<gv", { noremap = true, silent = true })

-- increment/decrement numbers
-- keymap.set("n", "<leader>+", "<C-a>", { desc = "Increment number" }) -- increment
-- keymap.set("n", "<leader>-", "<C-x>", { desc = "Decrement number" }) -- decrement

-- set - to end of text instead of $, ` to beginning of text instead of ^
vim.keymap.set("n", "-", "$", { noremap = true, silent = true })
vim.keymap.set("n", "`", "^", { noremap = true, silent = true })

-- set R to Redo
vim.keymap.set("n", "R", "<C-r>", { noremap = true, silent = true })

-- write and quit
keymap.set("n", "<leader>w", "<cmd>w<CR>", { desc = "Save file" }) -- save
keymap.set("n", "<leader>q", "<cmd>q<CR>", { desc = "Quit" }) -- quit

-- window management
keymap.set("n", "<leader>sv", "<C-w>v", { desc = "Split window vertically" }) -- split window vertically
keymap.set("n", "<leader>sh", "<C-w>s", { desc = "Split window horizontally" }) -- split window horizontally
keymap.set("n", "<leader>se", "<C-w>=", { desc = "Make splits equal size" }) -- make split windows equal width & height
keymap.set("n", "<leader>sx", "<cmd>close<CR>", { desc = "Close current split" }) -- close current split window

keymap.set("n", "<leader>to", "<cmd>tabnew<CR>", { desc = "Open new tab" }) -- open new tab
keymap.set("n", "<leader>tx", "<cmd>tabclose<CR>", { desc = "Close current tab" }) -- close current tab
-- keymap.set("n", "<leader>tn", "<cmd>tabn<CR>", { desc = "Go to next tab" }) --  go to next tab
-- keymap.set("n", "<leader>tp", "<cmd>tabp<CR>", { desc = "Go to previous tab" }) --  go to previous tab
keymap.set("n", "<leader>tf", "<cmd>tabnew %<CR>", { desc = "Open current file in new tab" }) --  move current buffer to new tab
keymap.set("n", "<Tab>", "<cmd>tabn<CR>", { desc = "Go to next tab" })
keymap.set("n", "<S-Tab>", "<cmd>tabp<CR>", { desc = "Go to previous tab" })

-- primeagen move lines up and down
keymap.set("v", "J", ":m '>+1<CR>gv=gv")
keymap.set("v", "K", ":m '<-2<CR>gv=gv")

-- go to start and end of file
keymap.set({ "n", "v" }, "<leader>gs", "<cmd>1<CR>", { desc = "Go to start of file" })
keymap.set({ "n", "v" }, "<leader>ge", "<cmd>$<CR>", { desc = "Go to end of file" })
