-- Set leader key before any keymaps
vim.g.mapleader = " "

vim.cmd("let g:netrw_liststyle = 3")

local opt = vim.opt

opt.relativenumber = true
opt.number = true

-- tabs & indentation
opt.tabstop = 4
opt.shiftwidth = 4
opt.expandtab = true -- expand tab to spaces
opt.autoindent = true -- copy indent from current line when starting new one

opt.wrap = false

-- search settings
opt.ignorecase = true -- ignore case when searching
opt.smartcase = true -- if you include mixed case in your search, assumes you want case-sensitive

opt.cursorline = true

-- turn on termguicolors for tokyonight colorscheme to work
-- (have to use iterm2 or any other true color terminal)
opt.termguicolors = true
opt.background = "dark" -- colorschemes that can be light or dark will be made dark
opt.signcolumn = "yes" -- show sign column so that text doesn't shift

-- backspace
opt.backspace = "indent,eol,start" -- allow backspace on indent, end of line or insert mode start position

-- clipboard
opt.clipboard:append("unnamedplus") -- use system clipboard as default register

-- split windows
opt.splitright = true -- split vertical window to the right
opt.splitbelow = true -- split horizontal window to the bottom

-- turn off swapfile
opt.swapfile = false
opt.autoread = true
opt.updatetime = 50 -- instant like VS Code (was 200)
opt.endofline = true
opt.fixendofline = true

-- highlight on yank
vim.api.nvim_create_autocmd("TextYankPost", {
	desc = "Highlight when yanking text",
	group = vim.api.nvim_create_augroup("highlight_yank", { clear = true }),
	callback = function()
		vim.highlight.on_yank({
			higroup = "IncSearch", -- highlight group
			timeout = 200, -- duration in ms
		})
	end,
})

vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold", "CursorHoldI", "CursorMoved", "CursorMovedI", "InsertLeave", "BufWritePost", "TermClose", "TermLeave" }, {
	group = vim.api.nvim_create_augroup("checktime", { clear = true }),
	callback = function()
		if vim.fn.getcmdwintype() == "" and vim.fn.mode() ~= "c" then
			vim.cmd("checktime")
		end
	end,
})

-- VS Code-like instant file watching: poll `checktime` every 50ms via libuv (FSEvents is event-driven on macOS)
-- store in _G to prevent GC
_G._autoread_timer = (vim.uv or vim.loop).new_timer()
_G._autoread_timer:start(50, 50, vim.schedule_wrap(function()
	if vim.fn.getcmdwintype() == "" and vim.fn.mode() ~= "c" then
		vim.cmd("silent! checktime")
	end
end))

-- notify when file changes on disk (reloaded by autoread)
vim.api.nvim_create_autocmd("FileChangedShellPost", {
	group = vim.api.nvim_create_augroup("autoread_notify", { clear = true }),
	callback = function()
		vim.notify("File changed on disk. Buffer reloaded.", vim.log.levels.WARN)
	end,
})

vim.api.nvim_create_autocmd("BufWritePre", {
	group = vim.api.nvim_create_augroup("trim_trailing_whitespace", { clear = true }),
	callback = function()
		local view = vim.fn.winsaveview()
		local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)

		for index, line in ipairs(lines) do
			lines[index] = line:gsub("%s+$", "")
		end
		while #lines > 1 and lines[#lines] == "" do
			table.remove(lines)
		end

		vim.api.nvim_buf_set_lines(0, 0, -1, false, lines)
		vim.fn.winrestview(view)
	end,
})
