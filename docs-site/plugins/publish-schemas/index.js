const fs = require('node:fs/promises');
const path = require('node:path');

module.exports = function publishSchemasPlugin(context) {
  const schemaSource = path.resolve(
    context.siteDir,
    '../src/pad_lattice/schemas',
  );

  return {
    name: 'publish-pad-lattice-schemas',
    async postBuild({outDir}) {
      await fs.cp(schemaSource, path.join(outDir, 'schemas'), {
        recursive: true,
      });
    },
  };
};
