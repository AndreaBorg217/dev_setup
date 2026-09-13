return {
	-- Ruff LSP provides: quickfix (F401, etc), source.fixAll, source.organizeImports
	-- Disable hover so pyright remains the hover provider (avoids duplicate hover)
	init_options = {
		settings = {
			lineLength = 120,
			lint = {
				select = { "ALL" },
				ignore = { "CPY001" },
				preview = true,
			},
		},
	},
	on_attach = function(client, _bufnr)
		-- let pyright handle hover/definition; ruff is lint+fix only
		if client.name == "ruff" then
			client.server_capabilities.hoverProvider = false
		end
	end,
}
