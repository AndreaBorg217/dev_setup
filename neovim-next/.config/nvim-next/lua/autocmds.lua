vim.api.nvim_create_autocmd("FileType", {
    group = vim.api.nvim_create_augroup("word_wrap_markdown_plaintext", { clear = true }),
    pattern = { "markdown", "text" },
    callback = function()
        vim.opt_local.wrap = true        -- Wrap prose within the window.
        vim.opt_local.linebreak = true   -- Break wrapped lines at word boundaries.
        vim.opt_local.breakindent = true -- Keep indentation on wrapped lines.
        vim.opt_local.showbreak = ""     -- Show no prefix on wrapped lines.
    end,
})

vim.api.nvim_create_autocmd("TextYankPost", {
    desc = "Highlight when yanking text",
    group = vim.api.nvim_create_augroup("highlight_yank", { clear = true }),
    callback = function()
        vim.hl.on_yank({ higroup = "IncSearch", timeout = 200 })
    end,
})

vim.api.nvim_create_autocmd("BufReadPost", {
    desc = "Restore the cursor to its last position in the file",
    callback = function(event)
        local position = vim.api.nvim_buf_get_mark(event.buf, '"')
        if position[1] > 0 and position[1] <= vim.api.nvim_buf_line_count(event.buf) then
            vim.fn.cursor(position[1], position[2] + 1)
        end
    end,
})

-- autoread reloads external changes only when checktime runs.
_G._autoread_timer = (vim.uv or vim.loop).new_timer()
_G._autoread_timer:start(
    50,
    50,
    vim.schedule_wrap(function()
        if vim.fn.getcmdwintype() == "" and vim.fn.mode() ~= "c" then
            vim.cmd("silent! checktime")
        end
    end)
)

vim.api.nvim_create_autocmd("BufWritePre", {
    group = vim.api.nvim_create_augroup("trim_trailing_whitespace", { clear = true }),
    callback = function()
        local view = vim.fn.winsaveview()
        local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)

        for index, line in ipairs(lines) do
            local trimmed = line:gsub("%s+$", "")
            if trimmed ~= line then
                vim.api.nvim_buf_set_text(0, index - 1, #trimmed, index - 1, #line, {})
                lines[index] = trimmed
            end
        end
        while #lines > 1 and lines[#lines] == "" do
            table.remove(lines)
        end

        if #lines < vim.api.nvim_buf_line_count(0) then
            vim.api.nvim_buf_set_lines(0, #lines, -1, false, {})
        end
        vim.fn.winrestview(view)
    end,
})
