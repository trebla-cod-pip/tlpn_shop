from pathlib import Path

path = Path('store/models.py')
text = path.read_text()

save_start = text.index('    def save(')
super_line = '        super().save(*args, **kwargs)'
super_idx = text.index(super_line, save_start)
save_end = super_idx + len(super_line) + 1

new_save = f"""    def save(self, *args, **kwargs):
        image_changed = self._image_was_changed()

        if not self.slug:
            base_slug = translit_slug(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

        if self.image and (image_changed or not (self.image_webp_400 and self.image_webp_800)):
            self._generate_webp_variants()

"""
text = text[:save_start] + new_save + text[save_end:]

if 'def _image_was_changed' not in text:
    insert_pos = text.index('        return 0', save_start)
    insert_pos += len('        return 0\n')
    helper = """
    def _image_was_changed(self):
        if not self.pk:
            return bool(self.image)
        previous = (
            Product.objects.filter(pk=self.pk)
            .values_list('image', flat=True)
            .first()
        )
        return (previous or '') != (self.image.name or '')

    def _generate_webp_variants(self):
        try:
            with Image.open(self.image.path) as source:
                source = ImageOps.exif_transpose(source)
                if source.mode not in ('RGB', 'RGBA'):
                    source = source.convert('RGB')

                variants = {
                    'image_webp_400': 400,
                    'image_webp_800': 800,
                }
                updates = {}

                for field_name, width in variants.items():
                    content = self._build_webp_content(source, width)
                    if not content:
                        continue

                    field = getattr(self, field_name)
                    if field:
                        field.delete(save=False)

                    filename = self._webp_filename(width)
                    field.save(filename, content, save=False)
                    updates[field_name] = field.name
        except (FileNotFoundError, OSError):
            return

        if updates:
            Product.objects.filter(pk=self.pk).update(**updates)
            for field_name, value in updates.items():
                setattr(self, field_name, value)

    def _build_webp_content(self, source_image, width):
        src_width, src_height = source_image.size
        if src_width <= 0 or src_height <= 0:
            return None

        target_height = max(1, round(src_height * width / src_width))
        resized = source_image.resize((width, target_height), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        resized.save(buffer, format='WEBP', quality=82, method=6)
        return ContentFile(buffer.getvalue())

    def _webp_filename(self, width):
        return f'{Path(self.image.name).stem}-{width}.webp'

"""
    text = text[:insert_pos] + helper + text[insert_pos:]

path.write_text(text)
