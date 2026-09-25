local configured_tools = {}
for _, tool in ipairs(require("plugins.mason")) do
	configured_tools[tool[1]] = true
end

vim.api.nvim_create_user_command("NvimClean", function()
	-- Removed vim.pack specs become inactive after restarting Neovim.
	local unused_plugins = {}
	for _, plugin in ipairs(vim.pack.get()) do
		if not plugin.active then
			table.insert(unused_plugins, plugin.spec.name)
		end
	end

	local unused_packages = {}
	for _, package in ipairs(require("mason-registry").get_installed_packages()) do
		if not configured_tools[package.name] then
			table.insert(unused_packages, package)
		end
	end

	if #unused_plugins == 0 and #unused_packages == 0 then
		vim.notify("No unused Neovim plugins or Mason packages")
		return
	end

	if #unused_plugins > 0 then
		vim.pack.del(unused_plugins)
		vim.notify("Removed plugins: " .. table.concat(unused_plugins, ", "))
	end
	for _, package in ipairs(unused_packages) do
		package:uninstall({}, function(success, err)
			if success then
				vim.notify("Removed Mason package: " .. package.name)
			else
				vim.notify("Could not remove Mason package " .. package.name .. ": " .. tostring(err), vim.log.levels.ERROR)
			end
		end)
	end
end, { desc = "Remove unused Neovim plugins and Mason packages" })
