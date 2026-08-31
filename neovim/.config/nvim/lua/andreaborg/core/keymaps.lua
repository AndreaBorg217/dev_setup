local keymap = vim.keymap

local function current_file_path()
	local file_name = vim.api.nvim_buf_get_name(0)
	if file_name == "" then
		return ""
	end

	return vim.fn.fnamemodify(file_name, ":p")
end

local function relative_file_path()
	local path = current_file_path()
	if path == "" then
		return ""
	end

	return vim.fn.fnamemodify(path, ":.")
end

local function copy_to_clipboard(value)
	vim.fn.setreg("+", value)
end

local function copy_path_with_line()
	copy_to_clipboard(string.format("%s:%d", relative_file_path(), vim.fn.line(".")))
end

local function copy_path_with_visual_lines()
	local first_line = vim.fn.line("v")
	local last_line = vim.fn.line(".")
	if first_line > last_line then
		first_line, last_line = last_line, first_line
	end

	copy_to_clipboard(string.format("%s:%d:%d", relative_file_path(), first_line, last_line))
end

local function reveal_in_finder()
	local path = current_file_path()
	if path == "" then
		return
	end

	vim.system({ "open", "-R", path })
end

local function delete_unmodified_buffers()
	local current_buffer = vim.api.nvim_get_current_buf()
	local preserved_count = 0

	for _, buffer in ipairs(vim.api.nvim_list_bufs()) do
		if buffer ~= current_buffer and vim.bo[buffer].buflisted then
			if vim.bo[buffer].modified then
				preserved_count = preserved_count + 1
			else
				vim.api.nvim_buf_delete(buffer, { force = false })
			end
		end
	end

	vim.notify(string.format("Preserved %d modified buffer(s)", preserved_count))
end

keymap.set("n", "<Esc>", "<cmd>nohlsearch<CR>", { desc = "Clear search highlights" })
vim.keymap.set("i", "<S-Tab>", "<C-d>", { noremap = true, silent = true })
vim.keymap.set("n", "-", "$", { noremap = true, silent = true })
vim.keymap.set("n", "`", "^", { noremap = true, silent = true })
vim.keymap.set("n", "R", "<C-r>", { noremap = true, silent = true })
vim.keymap.set("v", "<Tab>", ">gv", { noremap = true, silent = true })
vim.keymap.set("v", "<S-Tab>", "<gv", { noremap = true, silent = true })

keymap.set("n", "<leader>w", "<cmd>w<CR>", { desc = "Save file" })
keymap.set("n", "<leader>q", "<cmd>q<CR>", { desc = "Quit" })
keymap.set("n", "<leader>sv", "<C-w>v", { desc = "Split window vertically" })
keymap.set("n", "<leader>sh", "<C-w>s", { desc = "Split window horizontally" })
keymap.set("n", "<leader>se", "<C-w>=", { desc = "Make splits equal size" })
keymap.set("n", "<leader>sx", "<cmd>close<CR>", { desc = "Close current split" })

keymap.set("n", "<leader>to", "<cmd>tabnew<CR>", { desc = "Open new tab" })
keymap.set("n", "<Tab>", "<cmd>tabn<CR>", { desc = "Go to next tab" })
keymap.set("n", "<S-Tab>", "<cmd>tabp<CR>", { desc = "Go to previous tab" })
keymap.set("v", "J", ":m '>+1<CR>gv=gv")
keymap.set("v", "K", ":m '<-2<CR>gv=gv")
keymap.set("n", "<leader>os", reveal_in_finder, { desc = "Reveal current file in Finder" })
keymap.set("n", "<leader>cn", copy_path_with_line, { desc = "Copy relative path and line" })
keymap.set("v", "<leader>cn", copy_path_with_visual_lines, { desc = "Copy relative path and lines" })
keymap.set({ "n", "v" }, "<leader>cr", function()
	copy_to_clipboard(relative_file_path())
end, { desc = "Copy relative path" })
keymap.set({ "n", "v" }, "<leader>cp", function()
	copy_to_clipboard(current_file_path())
end, { desc = "Copy absolute path" })

keymap.set("n", "<C-/>", function()
	require("lazy").load({ plugins = { "Comment.nvim" } })
	require("Comment.api").toggle.linewise.current()
end, { desc = "Toggle comment" })
keymap.set("v", "<C-/>", function()
	local escape = vim.api.nvim_replace_termcodes("<Esc>", true, false, true)
	vim.api.nvim_feedkeys(escape, "nx", false)
	require("lazy").load({ plugins = { "Comment.nvim" } })
	require("Comment.api").toggle.linewise(vim.fn.visualmode())
end, { desc = "Toggle comment" })

keymap.set("n", "<leader>x", delete_unmodified_buffers, { desc = "Delete unmodified buffers" })
