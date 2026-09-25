vim.g.mapleader = " " -- Use Space as the leader key.
vim.g.netrw_liststyle = 3 -- Show netrw files as a tree.

vim.opt.relativenumber = true -- Show relative line numbers away from the cursor.
vim.opt.number = true -- Show the current line's absolute number.

vim.opt.tabstop = 4 -- Display a tab as four columns.
vim.opt.shiftwidth = 4 -- Indent and dedent by four columns.
vim.opt.expandtab = true -- Insert spaces instead of tab characters.
vim.opt.autoindent = true -- Copy indentation from the previous line.
vim.opt.listchars = { tab = "┊ ", leadmultispace = "┊   " } -- Draw guides for tabs and four-space indentation.
vim.opt.list = true -- Show indentation guides defined by listchars.

vim.opt.wrap = false -- Keep code lines on one screen line by default.
vim.opt.ignorecase = true -- Ignore case in searches by default.
vim.opt.smartcase = true -- Match case when a search contains uppercase.
vim.opt.complete = { ".", "w", "b", "o" } -- Suggest words from open buffers and the active LSP omnifunc.
vim.opt.completeopt = { "menu", "menuone", "noselect", "popup" } -- Show suggestions and documentation without selecting a match.
vim.opt.autocomplete = true -- Trigger native completion while typing.

vim.opt.cursorline = true -- Highlight the cursor's line.
vim.opt.termguicolors = true -- Use 24-bit terminal colours.
vim.opt.background = "dark" -- Select dark variants of colour schemes.
vim.cmd.colorscheme("catppuccin") -- Use Neovim 0.12's bundled Catppuccin theme.
vim.opt.signcolumn = "yes" -- Reserve space for signs so text does not shift.
vim.opt.showtabline = 0 -- Hide the tabpage line; this config does not use tabs.

vim.opt.backspace = "indent,eol,start" -- Let Backspace cross indentation, lines and insert start.
vim.opt.clipboard:append("unnamedplus") -- Use the system clipboard for ordinary yanks and pastes.

vim.opt.splitright = true -- Open vertical splits to the right.
vim.opt.splitbelow = true -- Open horizontal splits below.

vim.opt.swapfile = false -- Do not create swap files.
vim.opt.undofile = true -- Keep undo history across Neovim sessions.
vim.opt.confirm = true -- Ask before closing a modified buffer.
vim.opt.autoread = true -- Reload externally changed files when Neovim checks them.
vim.opt.updatetime = 50 -- Trigger idle events after 50 ms.
vim.opt.endofline = true -- Record a final newline for the buffer.
vim.opt.fixendofline = true -- Write a final newline when saving.

vim.opt.cmdheight = 0 -- Show the command line only while it is in use.
vim.opt.winborder = "rounded" -- Give floating windows rounded default borders.

-- Use Neovim 0.12's experimental command-line and message UI.
require("vim._core.ui2").enable({})
