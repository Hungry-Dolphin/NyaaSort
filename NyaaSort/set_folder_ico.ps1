$TargetDirectory = $args[0]
$anime = $args[1]

$DesktopIni = @"
[.ShellClassInfo]
IconResource=$TargetDirectory\$anime.ico,0
[ViewState]
Mode=
Vid=
FolderType=Pictures
Mode=4
"@
# The number behind iconresource is 0 for the first item
# The viewstate is how the folder is displayed 4 is for details
# This needs to be refreshed for some reason or windows won't detect the icon change
# Not sure why , if somebody knows a better way lemme know
# https://hwiegman.home.xs4all.nl/desktopini.html good reading material


If (Test-Path -LiteralPath "$($TargetDirectory)\desktop.ini")  {
  Write-Warning "The desktop.ini file already exists."
}
Else  {
  #Create/Add content to the desktop.ini file
  Add-Content -LiteralPath "$($TargetDirectory)\desktop.ini" -Value $DesktopIni

  #Set the attributes for $DesktopIni
  (Get-Item -LiteralPath "$($TargetDirectory)\desktop.ini" -Force).Attributes = 'Hidden, System, Archive'

  #Finally, set the folder's attributes
  (Get-Item -LiteralPath $TargetDirectory -Force).Attributes = 'ReadOnly, Directory'
}

# My powershell knowlegde is not the best so there is probs a better way to do this