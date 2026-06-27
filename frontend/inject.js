const fs = require('fs');
const path = require('path');

const dir = 'e:/Project/LIFEOS/frontend';
const files = fs.readdirSync(dir).filter(f => f.endsWith('.html'));

const injectStr = `
    <!-- ClickSpark -->
    <script src="js/click-spark.js"></script>
    <click-spark spark-color="#7C5CFF" spark-size="12" spark-radius="25" spark-count="10" duration="500"></click-spark>
`;

for (const file of files) {
  const p = path.join(dir, file);
  let content = fs.readFileSync(p, 'utf8');
  if (content.includes('click-spark.js')) continue;

  if (content.includes('</body>')) {
    content = content.replace('</body>', injectStr + '\n</body>');
  } else if (content.includes('</html>')) {
    content = content.replace('</html>', injectStr + '\n</body>\n</html>');
  } else {
    content += injectStr;
  }
  fs.writeFileSync(p, content);
  console.log('Injected into ' + file);
}
