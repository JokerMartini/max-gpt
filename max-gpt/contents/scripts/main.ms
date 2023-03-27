fn main =
(
	local dir = getFilenamePath(getSourceFileName())
	format "Executing Python Startup Scripts '%' ...\n" dir
	local files = sort(getFiles (dir + "\*.py"))
	for f in files do 
	(
		try 
		( 
			format "\t+ Executing %\n" f
			python.executeFile f 
		)
		catch
		(
			format "Failed to execute %\n" f
			format "*** % ***\n" (getCurrentException())
		)
	)
)

main()