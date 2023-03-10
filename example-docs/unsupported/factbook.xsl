<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:template match="/">
<html>
<body>
  <h2>World Factbook</h2>
  <table border="1">
    <tr bgcolor="#9acd32">
      <th style="text-align:left">Country</th>
      <th style="text-align:left">Capital</th>
      <th style="text-align:left">Leader</th>
      <th style="text-align:left">Sport</th>
    </tr>
    <xsl:for-each select="factbook/country">
    <tr>
      <td><xsl:value-of select="name"/></td>
      <td><xsl:value-of select="capital"/></td>
      <td><xsl:value-of select="leader"/></td>
      <td><xsl:value-of select="sport"/></td>
    </tr>
    </xsl:for-each>
  </table>
</body>
</html>
</xsl:template>
</xsl:stylesheet>
