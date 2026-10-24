param([string]$OntologyPath = '')
$ErrorActionPreference = 'Stop'
$protegeDirectory = Join-Path $PSScriptRoot 'tools/protege/Protege-5.6.9'
$ontology = if ($OntologyPath) { (Resolve-Path -LiteralPath $OntologyPath).Path } elseif (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'data/pharmagraph-complet.owl')) { Join-Path $PSScriptRoot 'data/pharmagraph-complet.owl' } else { Join-Path $PSScriptRoot 'data/pharmagraph.owl' }
if (-not (Test-Path -LiteralPath (Join-Path $protegeDirectory 'bundles/protege-launcher.jar'))) {
    throw 'Protégé est absent du dossier tools/protege/Protege-5.6.9.'
}
$javaExecutable = (Get-Command javaw.exe -ErrorAction Stop).Source
$ontologyUri = ([System.Uri]$ontology).AbsoluteUri
$classPath = 'bundles/guava.jar;bundles/logback-classic.jar;bundles/logback-core.jar;bundles/slf4j-api.jar;bundles/glassfish-corba-orb.jar;bundles/org.apache.felix.main.jar;bundles/maven-artifact.jar;bundles/protege-launcher.jar'
$launchArguments = @(
    '-XX:CompileCommand=exclude,javax/swing/text/GlyphView,getBreakSpot',
    '-DentityExpansionLimit=100000000',
    '-Dlogback.configurationFile=conf/logback-win.xml',
    '-Dfile.encoding=utf-8',
    '-Dorg.protege.plugin.dir=plugins',
    '-classpath', $classPath,
    'org.protege.osgi.framework.Launcher', $ontologyUri
)
Start-Process -FilePath $javaExecutable -ArgumentList $launchArguments -WorkingDirectory $protegeDirectory -WindowStyle Hidden
