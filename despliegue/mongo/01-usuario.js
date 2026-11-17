// Se ejecuta una sola vez al crear el volumen de MongoDB.
// oirs_app solo puede leer/escribir la base documental (y administrar la base de pruebas).
db.getSiblingDB("admin").createUser({
  user: "oirs_app",
  pwd: process.env.MONGO_APP_PASSWORD,
  roles: [
    { role: "readWrite", db: "oirs_plc_docs" },
    { role: "readWrite", db: "oirs_plc_docs_test" },
    { role: "dbAdmin", db: "oirs_plc_docs_test" },
  ],
});
