return {
	settings = {
		pyright = {
			-- let Ruff handle imports (official Ruff docs: disableOrganizeImports)
			disableOrganizeImports = true,
		},
		python = {
			analysis = {
				autoSearchPaths = true,
				diagnosticMode = "workspace",
				useLibraryCodeForTypes = true,
				typeCheckingMode = "standard",
				diagnosticSeverityOverrides = {
					reportUnusedImport = "none", -- Ruff F401 already reports this; avoids `sys imported but unused` + `"sys" is not accessed` duplication
					reportUnusedVariable = "none", -- Ruff F841 covers this; drop this line if you prefer Pyright's version
				},
			},
		},
	},
}
