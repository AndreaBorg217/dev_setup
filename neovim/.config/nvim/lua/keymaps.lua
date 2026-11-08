vim.keymap.set("i", "<S-Tab>", "<C-d>", { desc = "Outdent line", silent = true })
vim.keymap.set("n", "-", "$", { desc = "Go to end of line", silent = true })
vim.keymap.set("n", "`", "^", { desc = "Go to start of text", silent = true })
vim.keymap.set("n", "R", "<C-r>", { desc = "Redo", silent = true })

vim.keymap.set("v", "<Tab>", ">gv", { desc = "Indent selection", silent = true })
vim.keymap.set("v", "<S-Tab>", "<gv", { desc = "Outdent selection", silent = true })
vim.keymap.set("v", "J", ":m '>+1<CR>gv=gv", { desc = "Move selection down" })
vim.keymap.set("v", "K", ":m '<-2<CR>gv=gv", { desc = "Move selection up" })

vim.keymap.set("n", "<leader>w", "<cmd>w<CR>", { desc = "Save file" })
vim.keymap.set("n", "<leader>q", "<cmd>q<CR>", { desc = "Quit" })
vim.keymap.set("n", "<leader>sv", "<C-w>v", { desc = "Split window vertically" })
vim.keymap.set("n", "<leader>sh", "<C-w>s", { desc = "Split window horizontally" })
vim.keymap.set("n", "<leader>sx", "<cmd>close<CR>", { desc = "Close current split" })

vim.keymap.set("n", "<leader>os", function()
	local path = vim.fn.expand("%:p")
	if path == "" then
		return
	end

	vim.system({ "open", "-R", path })
end, { desc = "Reveal current file in Finder" })

vim.keymap.set("n", "<leader>cn", function()
	local path = vim.fn.expand("%:.")
	vim.fn.setreg("+", string.format("%s:%d", path, vim.fn.line(".")))
end, { desc = "Copy relative path and line" })

vim.keymap.set("v", "<leader>cn", function()
	local first_line = vim.fn.line("v")
	local last_line = vim.fn.line(".")
	if first_line > last_line then
		first_line, last_line = last_line, first_line
	end

	local path = vim.fn.expand("%:.")
	vim.fn.setreg("+", string.format("%s:%d:%d", path, first_line, last_line))
end, { desc = "Copy relative path and lines" })

vim.keymap.set({ "n", "v" }, "<leader>cr", function()
	vim.fn.setreg("+", vim.fn.expand("%:."))
end, { desc = "Copy relative path" })

vim.keymap.set({ "n", "v" }, "<leader>cp", function()
	vim.fn.setreg("+", vim.fn.expand("%:p"))
end, { desc = "Copy absolute path" })

for _, shortcut in ipairs({ "<C-/>", "<C-_>", "<D-/>" }) do
	vim.keymap.set("n", shortcut, "gcc", { desc = "Toggle comment", remap = true })
	vim.keymap.set("v", shortcut, "gc", { desc = "Toggle comment", remap = true })
	vim.keymap.set("i", shortcut, "<C-o>gcc", { desc = "Toggle comment", remap = true })
end
