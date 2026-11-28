local config = require("config")
local virtualtext
vim.keymap.set("i", "<Tab>", function()
	if vim.snippet.active({ direction = 1 }) then
		vim.snippet.jump(1)
	elseif vim.fn.pumvisible() == 1 and vim.fn.complete_info({ "selected" }).selected >= 0 then
		vim.api.nvim_feedkeys(vim.keycode("<C-y>"), "n", false)
	elseif virtualtext and virtualtext.action.is_visible() then
		virtualtext.action.accept()
	else
		vim.api.nvim_feedkeys(vim.keycode("<Tab>"), "n", false)
	end
end, { desc = "Accept snippet, completion, or inline suggestion" })

if config.ENABLE_AI_AUTOCOMPLETE == false then
	return
end

local selected = config.AUTOCOMPLETE
if vim.fn.executable("curl") == 0 then
	vim.notify("Minuet requires curl", vim.log.levels.WARN)
	return
end
if vim.fn.executable("ollama") == 0 then
	vim.notify("Ollama is unavailable", vim.log.levels.WARN)
	return
end
vim.fn.system({ "ollama", "show", selected.model })
if vim.v.shell_error ~= 0 then
	vim.notify("Ollama model unavailable: " .. selected.model, vim.log.levels.WARN)
	return
end

vim.pack.add({ "https://github.com/milanglacier/minuet-ai.nvim" }, { confirm = false })
require("minuet").setup({
	provider = "openai_fim_compatible",
	n_completions = 1,
	context_window = 512,
	debounce = selected.debounce_ms,
	throttle = selected.throttle_ms,
	request_timeout = 10,
	provider_options = {
		openai_fim_compatible = {
			name = "Ollama",
			-- Minuet requires a bearer value; Ollama ignores it.
			api_key = function() return "ollama" end,
			end_point = "http://localhost:11434/v1/completions",
			model = selected.model,
			optional = { max_tokens = 56, temperature = 0 },
		},
	},
	virtualtext = { auto_trigger_ft = { "*" }, show_on_completion_menu = true },
})

vim.system({
	"curl", "--silent", "--output", "/dev/null", "--max-time", "30",
	"--header", "Content-Type: application/json",
	"--data", vim.json.encode({ model = selected.model, prompt = "", stream = false, keep_alive = -1 }),
	"http://127.0.0.1:11434/api/generate",
})

virtualtext = require("minuet.virtualtext")
