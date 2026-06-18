# ===========================================================================
# Dockerfile — FreeRADIUS 3.2.x
# Base: debian bookworm untuk kompatibilitas terbaik dengan FreeRADIUS 3.2.x
# ===========================================================================

FROM debian:bookworm-slim AS freeradius

ENV DEBIAN_FRONTEND=noninteractive

# Install FreeRADIUS + modul PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    freeradius \
    freeradius-postgresql \
    freeradius-utils \
    && rm -rf /var/lib/apt/lists/*

# Hapus konfigurasi default yang tidak dibutuhkan
RUN rm -f /etc/freeradius/3.0/sites-enabled/default \
          /etc/freeradius/3.0/sites-enabled/inner-tunnel

# Copy konfigurasi Radiux ke dalam container
COPY freeradius/mods-available/sql /etc/freeradius/3.0/mods-available/sql
COPY freeradius/mods-config/sql/main/postgresql/ /etc/freeradius/3.0/mods-config/sql/main/postgresql/
COPY freeradius/dictionary.vendor/ /etc/freeradius/3.0/dictionary.vendor/
COPY freeradius/sites-available/ /etc/freeradius/3.0/sites-available/

# Enable modul SQL dan sites via symlink
RUN ln -sf /etc/freeradius/3.0/mods-available/sql \
           /etc/freeradius/3.0/mods-enabled/sql \
    && ln -sf /etc/freeradius/3.0/sites-available/default \
              /etc/freeradius/3.0/sites-enabled/default \
    && ln -sf /etc/freeradius/3.0/sites-available/inner-tunnel \
              /etc/freeradius/3.0/sites-enabled/inner-tunnel

# RADIUS ports
EXPOSE 1812/udp 1813/udp

# Jalankan sebagai foreground process agar Docker dapat monitoring
# -X = debug mode (gunakan di development, ganti dengan -f untuk production)
CMD ["freeradius", "-f", "-l", "stdout"]
